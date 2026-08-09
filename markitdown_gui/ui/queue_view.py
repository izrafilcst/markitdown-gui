"""A lista da fila.

Um QListWidget que hospeda uma LinhaDaFila por item, e que acumula duas
funcoes de arraste ao mesmo tempo: reordenar por dentro e receber arquivos
de fora. Distinguir as duas e a parte delicada, e a regra e simples: se o
que chegou tem URLs, veio do Explorer e e adicao; se nao tem, e um item da
propria lista sendo movido.

As linhas sao reusadas, nunca recriadas. Recriar no meio de um lote de 200
arquivos perderia foco de teclado e posicao de rolagem a cada conclusao,
que e exatamente quando o usuario esta olhando para a tela.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem, QWidget

from ..jobs.models import Item
from . import theme
from .queue_row import LinhaDaFila

PAPEL_ID = Qt.ItemDataRole.UserRole

# A folha de estilo poe borda, padding e margem em QListWidget::item, e
# esse espaco sai da area util do widget embutido. Gravar no item o
# sizeHint cru da linha faz o conteudo ficar maior que o espaco recebido,
# e o nome do arquivo aparece cortado ao meio. Os valores abaixo espelham
# `QListWidget::item` em theme.py, e a checagem em `_ajustar_altura`
# conserta sozinha se aquela regra mudar sem que ninguem lembre daqui.
_BORDA_DO_ITEM = 1
_CHROME_VERTICAL = 2 * (_BORDA_DO_ITEM + theme.SPACE["sm"] + theme.SPACE["xs"])


class ListaDaFila(QListWidget):
    """Lista de itens da fila, reordenavel por arraste."""

    ordem_alterada = Signal(list)     # list[str] na nova ordem
    remover_pedido = Signal(str)
    repetir_pedido = Signal(str)
    abrir_pedido = Signal(str)
    detalhe_pedido = Signal(str)      # adicao ao contrato 4.5, nao alteracao
    arquivos_soltos = Signal(list)    # list[Path]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ListaDaFila")
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.setAccessibleName("Fila de conversao")
        self._linhas: dict[str, LinhaDaFila] = {}

    # leitura

    def linha(self, item_id: str) -> LinhaDaFila | None:
        return self._linhas.get(item_id)

    def ordem_atual(self) -> list[str]:
        return [
            self.item(i).data(PAPEL_ID)
            for i in range(self.count())
        ]

    # comandos

    def adicionar(self, itens: list[Item]) -> None:
        for item in itens:
            if item.id in self._linhas:
                continue
            linha = LinhaDaFila(item)
            linha.remover_pedido.connect(self.remover_pedido.emit)
            linha.repetir_pedido.connect(self.repetir_pedido.emit)
            linha.abrir_pedido.connect(self.abrir_pedido.emit)
            linha.detalhe_pedido.connect(self.detalhe_pedido.emit)

            casca = QListWidgetItem(self)
            casca.setData(PAPEL_ID, item.id)
            casca.setSizeHint(self._altura_necessaria(linha))
            self.addItem(casca)
            self.setItemWidget(casca, linha)
            self._linhas[item.id] = linha

    def atualizar(self, item: Item) -> None:
        linha = self._linhas.get(item.id)
        if linha is None:
            return
        linha.atualizar(item)
        casca = self._casca(item.id)
        if casca is not None:
            casca.setSizeHint(self._altura_necessaria(linha))

    def remover(self, item_ids: list[str]) -> None:
        alvo = set(item_ids)
        for i in range(self.count() - 1, -1, -1):
            casca = self.item(i)
            if casca.data(PAPEL_ID) in alvo:
                self._linhas.pop(casca.data(PAPEL_ID), None)
                self.takeItem(i)

    def limpar_tudo(self) -> None:
        self.clear()
        self._linhas.clear()

    # apoio

    def _altura_necessaria(self, linha: LinhaDaFila) -> QSize:
        """Altura do conteudo mais o espaco que a folha de estilo consome."""
        pedido = linha.sizeHint()
        return QSize(pedido.width(), pedido.height() + _CHROME_VERTICAL)

    def _ajustar_alturas(self) -> None:
        """Corrige qualquer linha que ainda esteja recebendo menos do que pede.

        Existe como rede de seguranca: se alguem mexer no padding de
        `QListWidget::item` sem atualizar _CHROME_VERTICAL, o conteudo
        voltaria a ser cortado em silencio. Aqui a diferenca e medida no
        widget de verdade e devolvida ao item.
        """
        for i in range(self.count()):
            casca = self.item(i)
            linha = self._linhas.get(casca.data(PAPEL_ID))
            if linha is None:
                continue
            falta = linha.sizeHint().height() - linha.height()
            if falta > 0:
                atual = casca.sizeHint()
                casca.setSizeHint(QSize(atual.width(), atual.height() + falta))

    def showEvent(self, evento) -> None:
        super().showEvent(evento)
        self._ajustar_alturas()

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self._ajustar_alturas()

    def _casca(self, item_id: str) -> QListWidgetItem | None:
        for i in range(self.count()):
            casca = self.item(i)
            if casca.data(PAPEL_ID) == item_id:
                return casca
        return None

    def anunciar_ordem(self) -> None:
        self.ordem_alterada.emit(self.ordem_atual())

    def mover_para_teste(self, de: int, para: int) -> None:
        """Move uma linha de posicao sem depender de arraste do sistema.

        Existe porque simular um arraste interno de verdade exigiria o
        gerenciador de janelas, que nao existe no modo offscreen dos
        testes. O caminho de producao continua sendo o dropEvent.
        """
        casca = self.takeItem(de)
        item_id = casca.data(PAPEL_ID)
        linha = self._linhas.get(item_id)
        self.insertItem(para, casca)
        if linha is not None:
            casca.setSizeHint(self._altura_necessaria(linha))
            self.setItemWidget(casca, linha)

    # arraste

    def dragEnterEvent(self, evento: QDragEnterEvent) -> None:
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
            return
        super().dragEnterEvent(evento)

    def dragMoveEvent(self, evento: QDragEnterEvent) -> None:
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
            return
        super().dragMoveEvent(evento)

    def dropEvent(self, evento: QDropEvent) -> None:
        mime = evento.mimeData()

        # Veio de fora: adicionar, nunca reordenar.
        if mime.hasUrls():
            caminhos = [
                Path(url.toLocalFile())
                for url in mime.urls()
                if url.isLocalFile() and url.toLocalFile()
            ]
            if caminhos:
                evento.acceptProposedAction()
                self.arquivos_soltos.emit(caminhos)
            else:
                evento.ignore()
            return

        # Veio de dentro: o QListWidget reposiciona, e nos anunciamos.
        super().dropEvent(evento)
        self._recolar_widgets()
        self.anunciar_ordem()

    def _recolar_widgets(self) -> None:
        """Reassocia cada LinhaDaFila a sua casca depois de um InternalMove.

        O QListWidget move a casca, mas o widget embutido nao acompanha
        sozinho: sem isto a lista fica com linhas em branco depois do
        primeiro arraste.
        """
        for i in range(self.count()):
            casca = self.item(i)
            linha = self._linhas.get(casca.data(PAPEL_ID))
            if linha is not None and self.itemWidget(casca) is not linha:
                casca.setSizeHint(linha.sizeHint())
                self.setItemWidget(casca, linha)


def _demonstracao() -> int:  # pragma: no cover
    """Janela de demonstracao com um item em cada estado."""
    import sys

    from PySide6.QtWidgets import QApplication

    from ..jobs.models import Estado
    from . import theme

    app = QApplication(sys.argv)
    theme.aplicar(app)

    lista = ListaDaFila()
    lista.setWindowTitle("Demonstracao da fila")
    lista.resize(680, 420)

    exemplos = []
    for estado in Estado:
        item = Item(origem=Path(f"exemplo_{estado.value}.pdf"), estado=estado)
        if estado is Estado.FALHOU:
            item.mensagem = "Nao foi possivel ler o arquivo"
            item.detalhe = "FileConversionException: arquivo protegido por senha"
        exemplos.append(item)

    lista.adicionar(exemplos)
    for item in exemplos:
        lista.atualizar(item)

    lista.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_demonstracao())
