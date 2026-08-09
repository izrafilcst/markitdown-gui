"""Barra que mostra e escolhe a pasta de destino dos arquivos convertidos.

Ela aceita pasta solta, pelo mesmo motivo que a zona de arraste aceita
arquivo solto: no Windows, arrastar do Explorer e o gesto natural, e
obrigar o usuario a atravessar um dialogo de pasta para algo que ele ja
tem aberto na tela e atrito puro.

Soltar um arquivo aqui tambem funciona, e vira a pasta que o contem. Seria
tecnicamente defensavel recusar, mas a intencao de quem faz isso e obvia e
recusar so faria o usuario repetir o gesto no lugar certo.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from . import icons, theme

# A copia precisa bater com o comportamento: o controller recusa converter
# sem destino. Prometer "na mesma pasta do original" faria a interface
# mentir, e o usuario descobriria o erro so ao clicar em Converter.
SEM_DESTINO = "Nenhuma pasta escolhida ainda"
ALVO_MINIMO = 32


class BarraDestino(QFrame):
    """Mostra o destino atual, deixa trocar, e aceita pasta solta."""

    destino_escolhido = Signal(object)   # Path
    abrir_pasta = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BarraDestino")
        self.setAcceptDrops(True)
        self.setAccessibleName("Pasta de destino")

        self._destino: Path | None = None
        self._sob_arraste = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            theme.SPACE["md"], theme.SPACE["sm"], theme.SPACE["md"], theme.SPACE["sm"]
        )
        layout.setSpacing(theme.SPACE["sm"])

        self._icone = QLabel()
        self._icone.setPixmap(icons.pixmap("pasta", theme.COLOR["ink_soft"], 20))

        self._rotulo = QLabel("Salvar em:")
        self._rotulo.setObjectName("BarraDestinoRotulo")

        self._caminho = QLabel(SEM_DESTINO)
        self._caminho.setObjectName("BarraDestinoCaminho")
        self._caminho.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.botao_escolher = QPushButton("Escolher pasta")
        self.botao_escolher.setAccessibleName("Escolher pasta de destino")
        self.botao_escolher.setMinimumSize(140, ALVO_MINIMO)
        self.botao_escolher.setIcon(icons.icone("pasta-aberta", theme.COLOR["ink"]))
        self.botao_escolher.clicked.connect(self._perguntar_pasta)

        self.botao_abrir = QPushButton()
        self.botao_abrir.setAccessibleName("Abrir a pasta de destino")
        self.botao_abrir.setToolTip("Abrir a pasta de destino")
        self.botao_abrir.setMinimumSize(ALVO_MINIMO, ALVO_MINIMO)
        self.botao_abrir.setIcon(icons.icone("abrir-externo", theme.COLOR["ink"]))
        self.botao_abrir.clicked.connect(self.abrir_pasta.emit)
        self.botao_abrir.setEnabled(False)

        layout.addWidget(self._icone)
        layout.addWidget(self._rotulo)
        layout.addWidget(self._caminho, 1)
        layout.addWidget(self.botao_escolher)
        layout.addWidget(self.botao_abrir)

        self._pintar()

    # estado

    def destino(self) -> Path | None:
        return self._destino

    def definir_destino(self, pasta: Path | None) -> None:
        """Reflete o destino atual na tela.

        NAO emite destino_escolhido de proposito: quem chama este metodo e
        a janela principal, repassando o que o controller ja decidiu. Se o
        setter emitisse, o sinal voltaria para o controller e viraria laco.
        """
        self._destino = pasta
        self._caminho.setText(str(pasta) if pasta is not None else SEM_DESTINO)
        self._caminho.setToolTip(str(pasta) if pasta is not None else SEM_DESTINO)
        self.botao_abrir.setEnabled(pasta is not None)

    def texto_do_destino(self) -> str:
        return self._caminho.text()

    # escolha por dialogo

    def _perguntar_pasta(self) -> None:
        inicial = str(self._destino) if self._destino is not None else ""
        escolhida = QFileDialog.getExistingDirectory(
            self, "Escolha a pasta de destino", inicial
        )
        if escolhida:
            self.destino_escolhido.emit(Path(escolhida))

    # aparencia

    def _pintar(self) -> None:
        borda = (
            theme.COLOR["accent"] if self._sob_arraste else theme.COLOR["border"]
        )
        fundo = (
            theme.COLOR["surface_alt"] if self._sob_arraste else theme.COLOR["surface"]
        )
        self.setStyleSheet(
            f"#BarraDestino {{"
            f" border: 1px solid {borda};"
            f" border-radius: {theme.RADIUS['md']}px;"
            f" background: {fundo};"
            f"}}"
        )

    def _marcar_arraste(self, ativo: bool) -> None:
        if ativo != self._sob_arraste:
            self._sob_arraste = ativo
            self._pintar()

    # arraste

    def dragEnterEvent(self, evento: QDragEnterEvent) -> None:
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
            self._marcar_arraste(True)
        else:
            evento.ignore()

    def dragMoveEvent(self, evento: QDragEnterEvent) -> None:
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dragLeaveEvent(self, evento: QDragLeaveEvent) -> None:
        self._marcar_arraste(False)
        evento.accept()

    def dropEvent(self, evento: QDropEvent) -> None:
        self._marcar_arraste(False)
        mime = evento.mimeData()
        if not mime.hasUrls():
            evento.ignore()
            return

        for url in mime.urls():
            if not url.isLocalFile():
                continue
            bruto = url.toLocalFile()
            if not bruto:
                continue
            caminho = Path(bruto)
            pasta = caminho if caminho.is_dir() else caminho.parent
            evento.acceptProposedAction()
            self.destino_escolhido.emit(pasta)
            return

        evento.ignore()
