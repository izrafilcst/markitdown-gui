"""A janela principal, que so integra: nao ha regra de negocio aqui.

Toda decisao sobre o que converter, com que nome e em que ordem mora no
FilaController. Esta classe conecta sinal em slot e desenha o resultado.
Quando alguem se pegar escrevendo um `if` sobre estado de conversao aqui
dentro, esse `if` provavelmente pertence ao controller.

A janela inteira aceita drop, nao so a zona de arraste. Quem arrasta do
Explorer mira na janela, nao num retangulo especifico dentro dela, e
recusar o drop porque caiu dois pixels fora da area seria hostil.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME
from ..core.historico import Historico
from ..jobs.controller import FilaController
from ..jobs.models import Item
from . import icons, theme
from .destino_bar import BarraDestino
from .drop_zone import DropZone
from .history_view import AbaRecentes
from .prefs import Preferencias
from .queue_view import ListaDaFila

ALVO_MINIMO = 32


class MainWindow(QMainWindow):
    """Junta zona de arraste, barra de destino, fila e rodape."""

    def __init__(
        self,
        parent: QWidget | None = None,
        historico_em: Path | None = None,
    ) -> None:
        """`historico_em` aponta o banco do historico. So os testes usam."""
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.setAcceptDrops(True)
        self.resize(880, 640)

        self.historico = Historico(historico_em)
        self.controller = FilaController(self, historico=self.historico)
        self.prefs = Preferencias()

        aba_fila = QWidget()
        layout = QVBoxLayout(aba_fila)
        layout.setContentsMargins(
            theme.SPACE["lg"], theme.SPACE["lg"], theme.SPACE["lg"], theme.SPACE["lg"]
        )
        layout.setSpacing(theme.SPACE["md"])

        self.barra_destino = BarraDestino()
        self.drop_zone = DropZone()
        self.lista = ListaDaFila()

        self.barra_aviso = QLabel()
        self.barra_aviso.setObjectName("BarraAviso")
        self.barra_aviso.setWordWrap(True)
        self.barra_aviso.setVisible(False)

        layout.addWidget(self.barra_destino)
        layout.addWidget(self.barra_aviso)
        layout.addWidget(self.drop_zone)
        layout.addWidget(self.lista, 1)
        layout.addLayout(self._montar_rodape())

        self.aba_recentes = AbaRecentes(self.historico)
        self.aba_recentes.abrir_pedido.connect(self._abrir_no_sistema)

        self.abas = QTabWidget()
        self.abas.addTab(aba_fila, "Fila")
        self.abas.addTab(self.aba_recentes, "Recentes")
        # A fila primeiro: quem abre o app quer converter, e nao consultar
        # o que ja converteu.
        self.abas.setCurrentIndex(0)
        self.abas.currentChanged.connect(self._ao_trocar_de_aba)

        self.setCentralWidget(self.abas)
        self._ligar_sinais()
        self._restaurar_preferencias()
        self._atualizar_controles()

    # montagem

    def _montar_rodape(self) -> QHBoxLayout:
        rodape = QHBoxLayout()
        rodape.setSpacing(theme.SPACE["sm"])

        self.rotulo_progresso = QLabel("Nada na fila")
        self.rotulo_progresso.setObjectName("RotuloProgresso")

        self.botao_pausar = QPushButton("Pausar")
        self.botao_pausar.setMinimumSize(110, ALVO_MINIMO)
        self.botao_pausar.setIcon(icons.icone("pausar", theme.COLOR["ink"]))
        self.botao_pausar.setEnabled(False)

        self.botao_limpar = QPushButton("Limpar fila")
        self.botao_limpar.setMinimumSize(120, ALVO_MINIMO)
        self.botao_limpar.setIcon(icons.icone("lixeira", theme.COLOR["ink"]))

        self.botao_converter = QPushButton("Converter")
        self.botao_converter.setObjectName("BotaoPrimario")
        self.botao_converter.setMinimumSize(140, 40)
        self.botao_converter.setIcon(icons.icone("tocar", theme.COLOR["on_primary"]))
        self.botao_converter.setDefault(True)

        rodape.addWidget(self.rotulo_progresso, 1)
        rodape.addWidget(self.botao_limpar)
        rodape.addWidget(self.botao_pausar)
        rodape.addWidget(self.botao_converter)
        return rodape

    def _ligar_sinais(self) -> None:
        c = self.controller

        self.drop_zone.arquivos_soltos.connect(c.adicionar)
        self.drop_zone.clicada.connect(self._escolher_arquivos)
        self.lista.arquivos_soltos.connect(c.adicionar)

        self.barra_destino.destino_escolhido.connect(c.definir_destino)
        self.barra_destino.abrir_pasta.connect(self._abrir_destino)

        self.lista.remover_pedido.connect(lambda i: c.remover([i]))
        self.lista.repetir_pedido.connect(lambda i: c.repetir([i]))
        self.lista.abrir_pedido.connect(self._abrir_convertido)
        self.lista.detalhe_pedido.connect(self._mostrar_detalhe)
        self.lista.ordem_alterada.connect(c.reordenar)

        c.itens_adicionados.connect(self._ao_adicionar)
        c.item_alterado.connect(self._ao_alterar_item)
        c.itens_removidos.connect(self._ao_remover)
        c.fila_limpa.connect(self._ao_limpar)
        c.progresso.connect(self._ao_progredir)
        c.ocioso.connect(self._ao_ficar_ocioso)
        c.aviso.connect(self._ao_avisar)
        c.destino_alterado.connect(self._ao_mudar_destino)

        self.botao_converter.clicked.connect(c.iniciar)
        self.botao_limpar.clicked.connect(c.limpar)
        self.botao_pausar.clicked.connect(self._alternar_pausa)

    def _restaurar_preferencias(self) -> None:
        destino = self.prefs.destino()
        if destino is not None:
            self.controller.definir_destino(destino)
        geometria = self.prefs.geometria()
        if geometria is not None:
            self.restoreGeometry(geometria)

    # leitura, usada pelos testes

    def texto_do_aviso(self) -> str:
        return self.barra_aviso.text()

    def texto_de_detalhe(self, item_id: str) -> str:
        item = self.controller.item(item_id)
        return item.detalhe if item is not None else ""

    # reacoes ao controller

    def _ao_adicionar(self, itens: list[Item]) -> None:
        self.lista.adicionar(itens)
        self._atualizar_controles()

    def _ao_alterar_item(self, item_id: str) -> None:
        item = self.controller.item(item_id)
        if item is not None:
            self.lista.atualizar(item)

    def _ao_remover(self, item_ids: list[str]) -> None:
        self.lista.remover(item_ids)
        self._atualizar_controles()

    def _ao_limpar(self) -> None:
        self.lista.limpar_tudo()
        self._atualizar_controles()

    def _ao_progredir(self, concluidos: int, falhas: int, total: int) -> None:
        if total == 0:
            self.rotulo_progresso.setText("Nada na fila")
            return
        partes = [f"{concluidos} de {total} convertidos"]
        if falhas:
            partes.append(f"{falhas} com falha")
        self.rotulo_progresso.setText(", ".join(partes))

    def _ao_ficar_ocioso(self) -> None:
        self._atualizar_controles()
        # A fila acabou, entao ha coisa nova no historico. Recarregar aqui
        # evita a aba mostrar dado velho se o usuario trocar de aba logo
        # depois de converter.
        self.aba_recentes.atualizar()

    def _ao_trocar_de_aba(self, indice: int) -> None:
        """Recarrega o historico ao entrar na aba dele.

        O banco pode ter mudado por outra janela do app aberta ao mesmo
        tempo, entao ler na hora de mostrar e mais honesto do que confiar
        no que foi carregado na abertura.
        """
        if self.abas.widget(indice) is self.aba_recentes:
            self.aba_recentes.atualizar()

    def _ao_avisar(self, nivel: str, texto: str) -> None:
        cor = theme.COLOR["warning_text" if nivel == "alerta" else "ink_soft"]
        self.barra_aviso.setText(texto)
        self.barra_aviso.setStyleSheet(f"color: {cor};")
        self.barra_aviso.setVisible(bool(texto))

    def _ao_mudar_destino(self, pasta: Path | None) -> None:
        self.barra_destino.definir_destino(pasta)
        if pasta is not None:
            self.prefs.definir_destino(pasta)

    # acoes do usuario

    def _escolher_arquivos(self) -> None:
        caminhos, _ = QFileDialog.getOpenFileNames(
            self, "Escolha os arquivos para converter"
        )
        if caminhos:
            self.controller.adicionar([Path(c) for c in caminhos])

    def _alternar_pausa(self) -> None:
        if self.controller.pausado:
            self.controller.retomar()
        else:
            self.controller.pausar()
        self._atualizar_controles()

    def _abrir_destino(self) -> None:
        destino = self.controller.destino
        if destino is not None:
            self._abrir_no_sistema(destino)

    def _abrir_convertido(self, item_id: str) -> None:
        item = self.controller.item(item_id)
        if item is not None and item.destino is not None:
            self._abrir_no_sistema(item.destino)

    def _abrir_no_sistema(self, caminho: Path) -> None:
        """Abre arquivo ou pasta no gerenciador do sistema.

        Sem QDesktopServices de proposito: no Windows ele as vezes falha
        silenciosamente para caminhos com acento, e falhar em silencio e o
        pior resultado possivel para um botao que o usuario acabou de
        clicar.
        """
        try:
            if sys.platform == "win32":
                os.startfile(str(caminho))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(caminho)], check=False)
            else:
                subprocess.run(["xdg-open", str(caminho)], check=False)
        except OSError as exc:
            self._ao_avisar("alerta", f"Nao foi possivel abrir: {exc}")

    def _mostrar_detalhe(self, item_id: str) -> None:
        item = self.controller.item(item_id)
        if item is None:
            return
        caixa = QMessageBox(self)
        caixa.setWindowTitle("Detalhe tecnico")
        caixa.setIcon(QMessageBox.Icon.Information)
        caixa.setText(item.mensagem or "Sem mensagem")
        caixa.setDetailedText(item.detalhe)
        caixa.exec()

    # estado dos controles

    def _atualizar_controles(self) -> None:
        tem_item = bool(self.controller.itens)
        self.botao_converter.setEnabled(tem_item)
        self.botao_pausar.setEnabled(self.controller.ativo)
        self.botao_pausar.setText("Retomar" if self.controller.pausado else "Pausar")
        self.botao_pausar.setIcon(
            icons.icone(
                "tocar" if self.controller.pausado else "pausar", theme.COLOR["ink"]
            )
        )
        self.drop_zone.definir_compacto(tem_item)

    # arraste na janela inteira

    def dragEnterEvent(self, evento: QDragEnterEvent) -> None:
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dragMoveEvent(self, evento: QDragEnterEvent) -> None:
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dropEvent(self, evento: QDropEvent) -> None:
        mime = evento.mimeData()
        if not mime.hasUrls():
            evento.ignore()
            return
        caminhos = [
            Path(url.toLocalFile())
            for url in mime.urls()
            if url.isLocalFile() and url.toLocalFile()
        ]
        if not caminhos:
            evento.ignore()
            return
        evento.acceptProposedAction()
        self.controller.adicionar(caminhos)

    # fechamento

    def closeEvent(self, evento: QCloseEvent) -> None:
        """Espera os workers antes de sair.

        Sem isto, fechar durante a conversao deixa python.exe orfao no
        Gerenciador de Tarefas, que e o item mais constrangedor do roteiro
        de verificacao manual.
        """
        self.prefs.definir_geometria(self.saveGeometry())
        self.controller.encerrar()
        super().closeEvent(evento)
