"""O cerebro da fila: quem entra, quem roda, quem termina.

Este e o unico modulo do app com concorrencia de verdade, e por isso ele
concentra as tres decisoes que mantem a coisa toda previsivel:

1. O nome do arquivo de saida e escolhido AQUI, na thread da interface, no
   momento do despacho. Se cada worker escolhesse o proprio nome, dois
   arquivos com o mesmo nome base convertidos ao mesmo tempo poderiam
   chamar `resolve_output_path` no mesmo instante, ver a mesma pasta vazia,
   e gravar um por cima do outro. Serializar a decisao aqui elimina a
   corrida sem precisar de lock.
2. So `min(4, cpu_count)` conversoes rodam juntas. Alem disso o ganho some e
   a memoria de quatro PDFs abertos ja e desconfortavel.
3. Nada aqui bloqueia a thread da interface, exceto `encerrar`, que espera
   os workers de proposito para nao deixar processo orfao no fechamento.

A interface le estado por propriedades e reage a sinais. Ela nunca mexe na
lista interna.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from ..core import discovery, naming
from .models import Estado, Item
from .worker import ConversionWorker


class FilaController(QObject):
    itens_adicionados = Signal(list)      # list[Item], ja na ordem de exibicao
    item_alterado = Signal(str)           # item_id
    itens_removidos = Signal(list)        # list[str]
    fila_limpa = Signal()
    progresso = Signal(int, int, int)     # concluidos, falhas, total
    ocioso = Signal()                     # nada mais a processar
    aviso = Signal(str, str)              # nivel ("info"|"alerta"), texto
    destino_alterado = Signal(object)     # Path

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._itens: list[Item] = []
        self._indice: dict[str, Item] = {}
        self._destino: Path | None = None
        self._pausado = False

        # Ligado por `iniciar` e desligado quando a fila esvazia. Serve para
        # que arrastar mais arquivos no meio de uma conversao em andamento
        # continue a conversao, sem que arrastar com a fila parada dispare
        # conversao sozinho.
        self._rodando = False

        # Nomes de saida ja prometidos a itens em voo. Sem isso, o segundo
        # worker so descobriria a colisao quando o primeiro ja tivesse
        # gravado, que e tarde demais.
        self._reservados: set[Path] = set()

        # Referencia forte aos workers em voo. Duas razoes: com autoDelete
        # ligado o pool destroi o QRunnable assim que `run` retorna, e o
        # objeto de sinais morre junto, podendo derrubar a entrega de um
        # sinal ainda em transito entre threads; e o dicionario tambem e o
        # contador de slots ocupados.
        self._workers: dict[str, ConversionWorker] = {}

        self._paralelismo = min(4, os.cpu_count() or 1)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(self._paralelismo)

    # ------------------------------------------------------------------
    # estado, somente leitura para a interface
    # ------------------------------------------------------------------

    @property
    def itens(self) -> list[Item]:
        """Copia da lista, para que a interface nao reordene por acidente.

        Os `Item` em si sao os mesmos objetos, de proposito: a linha da fila
        precisa enxergar a mudanca de estado sem copia intermediaria.
        """
        return list(self._itens)

    @property
    def destino(self) -> Path | None:
        return self._destino

    @property
    def pausado(self) -> bool:
        return self._pausado

    @property
    def ativo(self) -> bool:
        return any(
            i.estado in (Estado.PENDENTE, Estado.PROCESSANDO) for i in self._itens
        )

    def item(self, item_id: str) -> Item | None:
        return self._indice.get(item_id)

    # ------------------------------------------------------------------
    # comandos
    # ------------------------------------------------------------------

    def adicionar(self, caminhos: list[Path]) -> None:
        descoberta = discovery.expandir(
            caminhos, ja_na_fila={i.origem for i in self._itens}
        )

        novos = [Item(origem=arquivo) for arquivo in descoberta.aceitos]
        for item in novos:
            self._itens.append(item)
            self._indice[item.id] = item

        if novos:
            self.itens_adicionados.emit(novos)
            self._emitir_progresso()

        self._avisar_sobre(descoberta, novos)

        # Se ja havia conversao em andamento, o que acabou de chegar entra na
        # mesma leva em vez de esperar um novo clique em Converter.
        if self._rodando:
            self._despachar()

    def definir_destino(self, pasta: Path) -> None:
        novo = Path(pasta)
        if novo == self._destino:
            return
        self._destino = novo
        # As reservas valem por pasta. Trocar a pasta zera a contagem de
        # colisao, senao um nome livre no destino novo apareceria ocupado.
        self._reservados.clear()
        self.destino_alterado.emit(self._destino)

    def iniciar(self) -> None:
        if self._destino is None:
            self.aviso.emit(
                "alerta", "Escolha a pasta de destino antes de converter."
            )
            return
        self._rodando = True
        self._despachar()

    def pausar(self) -> None:
        # Para o despacho de itens novos. O que ja esta rodando termina,
        # porque nao ha como matar uma thread em Python sem risco de deixar
        # o arquivo pela metade.
        self._pausado = True

    def retomar(self) -> None:
        self._pausado = False
        if self._destino is not None:
            self._rodando = True
        self._despachar()

    def remover(self, item_ids: list[str]) -> None:
        alvos = set(item_ids)
        # Item em conversao e ignorado em silencio: a interface ja esconde o
        # botao de remover nesse estado, entao chegar aqui e caso de borda.
        removidos = [
            i.id
            for i in self._itens
            if i.id in alvos and i.estado is not Estado.PROCESSANDO
        ]
        if not removidos:
            return

        self._descartar(removidos)
        self.itens_removidos.emit(removidos)
        self._emitir_progresso()
        self._checar_ocioso()

    def limpar(self) -> None:
        removidos = [
            i.id for i in self._itens if i.estado is not Estado.PROCESSANDO
        ]
        if not removidos:
            return

        self._descartar(removidos)
        if self._itens:
            # Sobrou item em conversao, entao a lista nao foi zerada e a
            # interface precisa saber exatamente o que sumiu.
            self.itens_removidos.emit(removidos)
        else:
            self.fila_limpa.emit()
        self._emitir_progresso()
        self._checar_ocioso()

    def repetir(self, item_ids: list[str]) -> None:
        alterados = []
        for item_id in item_ids:
            item = self._indice.get(item_id)
            if item is None or not item.pode_repetir:
                continue
            # O nome prometido a tentativa anterior volta para o bolo, senao
            # cada repeticao gastaria um numero de sufixo.
            if item.destino is not None:
                self._reservados.discard(item.destino)
            item.reiniciar()
            alterados.append(item.id)

        for item_id in alterados:
            self.item_alterado.emit(item_id)
        if alterados:
            self._emitir_progresso()
            if self._rodando:
                self._despachar()

    def repetir_falhas(self) -> None:
        self.repetir([i.id for i in self._itens if i.pode_repetir])

    def reordenar(self, nova_ordem: list[str]) -> None:
        posicao = {item_id: n for n, item_id in enumerate(nova_ordem)}
        # Item fora da lista recebida fica no fim, na ordem em que ja estava:
        # `list.sort` e estavel, entao o desempate sai de graca.
        self._itens.sort(key=lambda i: posicao.get(i.id, len(posicao)))

    def encerrar(self) -> None:
        """Fecha a fila esperando os workers, para nao deixar processo orfao."""
        self._pausado = True
        self._rodando = False
        self._pool.clear()  # descarta o que ainda nao comecou
        self._pool.waitForDone()
        self._workers.clear()

    # ------------------------------------------------------------------
    # despacho
    # ------------------------------------------------------------------

    def _despachar(self) -> None:
        if not self._pausado and self._destino is not None:
            livres = self._paralelismo - len(self._workers)
            for item in self._itens:
                if livres <= 0:
                    break
                if item.estado is not Estado.PENDENTE:
                    continue
                if self._iniciar_item(item):
                    livres -= 1
        self._checar_ocioso()

    def _iniciar_item(self, item: Item) -> bool:
        """Reserva o nome de saida e joga o item no pool. True se despachou."""
        assert self._destino is not None
        try:
            destino = naming.resolve_output_path(
                item.origem, self._destino, self._reservados
            )
        except (OSError, RuntimeError) as exc:
            item.estado = Estado.FALHOU
            item.mensagem = "Não foi possível escolher um nome para a saída"
            item.detalhe = f"{type(exc).__name__}: {exc}"
            self.item_alterado.emit(item.id)
            self._emitir_progresso()
            return False

        self._reservados.add(destino)
        item.destino = destino
        item.estado = Estado.PROCESSANDO
        item.mensagem = ""
        item.detalhe = ""

        worker = ConversionWorker(item.id, item.origem, destino)
        # O pool nao pode destruir o worker: quem controla o tempo de vida
        # dele e o dicionario abaixo. Ver o comentario em __init__.
        worker.setAutoDelete(False)
        worker.sinais.concluiu.connect(self._ao_concluir)
        worker.sinais.falhou.connect(self._ao_falhar)
        self._workers[item.id] = worker

        self.item_alterado.emit(item.id)
        self._pool.start(worker)
        return True

    @Slot(str, str, int)
    def _ao_concluir(self, item_id: str, caminho: str, caracteres: int) -> None:
        self._workers.pop(item_id, None)
        item = self._indice.get(item_id)
        if item is not None:
            item.estado = Estado.CONCLUIDO
            item.destino = Path(caminho)
            item.caracteres = caracteres
            item.mensagem = ""
            item.detalhe = ""
            self.item_alterado.emit(item_id)
        self._emitir_progresso()
        self._despachar()

    @Slot(str, str, str)
    def _ao_falhar(self, item_id: str, mensagem: str, detalhe: str) -> None:
        self._workers.pop(item_id, None)
        item = self._indice.get(item_id)
        if item is not None:
            item.estado = Estado.FALHOU
            item.mensagem = mensagem
            item.detalhe = detalhe
            # Falhou, entao nada foi gravado com aquele nome: devolve a
            # reserva em vez de queimar o numero de sufixo.
            if item.destino is not None:
                self._reservados.discard(item.destino)
                item.destino = None
            self.item_alterado.emit(item_id)
        self._emitir_progresso()
        self._despachar()

    # ------------------------------------------------------------------
    # auxiliares
    # ------------------------------------------------------------------

    def _descartar(self, item_ids: list[str]) -> None:
        alvos = set(item_ids)
        for item_id in alvos:
            item = self._indice.pop(item_id, None)
            if item is not None and item.destino is not None:
                self._reservados.discard(item.destino)
        self._itens = [i for i in self._itens if i.id not in alvos]

    def _checar_ocioso(self) -> None:
        if not self._rodando or self._workers:
            return
        if any(i.estado is Estado.PENDENTE for i in self._itens):
            return
        self._rodando = False
        self.ocioso.emit()

    def _emitir_progresso(self) -> None:
        concluidos = sum(1 for i in self._itens if i.estado is Estado.CONCLUIDO)
        # Cancelado conta como falha para que concluidos mais falhas alcance
        # o total, senao a barra de progresso nunca fecha.
        falhas = sum(
            1 for i in self._itens if i.estado in (Estado.FALHOU, Estado.CANCELADO)
        )
        self.progresso.emit(concluidos, falhas, len(self._itens))

    def _avisar_sobre(
        self, descoberta: discovery.Descoberta, novos: list[Item]
    ) -> None:
        if descoberta.recusados:
            primeira = descoberta.recusados[0]
            if len(descoberta.recusados) == 1:
                texto = f"{primeira.path.name}: {primeira.motivo}."
            else:
                texto = (
                    f"{len(descoberta.recusados)} itens ficaram de fora. "
                    f"Por exemplo, {primeira.path.name}: {primeira.motivo}."
                )
            self.aviso.emit("alerta", texto)

        if descoberta.truncado:
            self.aviso.emit(
                "alerta",
                "Veio arquivo demais de uma vez. Foram aceitos os primeiros "
                f"{len(descoberta.aceitos)}, o resto ficou de fora.",
            )

        # Soltar arquivos que ja estao na fila e nao dizer nada faz o app
        # parecer quebrado. Este e o unico aviso de nivel informativo.
        if not novos and not descoberta.recusados and not descoberta.truncado:
            self.aviso.emit("info", "Esses arquivos já estão na fila.")
