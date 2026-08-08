"""A zona de arraste, que e a tela principal do app quando a fila esta vazia.

Dois tamanhos, nao dois widgets: grande quando nao ha nada na fila, porque
ai ela E a interface e nao um espaco morto, e uma faixa fina quando ja ha
itens, porque ai o que importa e a fila. A transicao anima a altura maxima.

Sobre o caminho absoluto: `QUrl.toLocalFile` e o motivo de o projeto ser
Qt e nao HTML. Um navegador entrega o conteudo do arquivo solto, nunca o
caminho, e converter em lote copiando gigabytes para uma pasta temporaria
seria absurdo. Aqui o caminho chega inteiro, e `test_drop.py` prova isso.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from . import icons, theme

ALTURA_GRANDE = 260
ALTURA_COMPACTA = 88


class DropZone(QFrame):
    """Area que aceita arquivos e pastas soltos do Explorer."""

    arquivos_soltos = Signal(list)   # list[Path]
    clicada = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Area para soltar arquivos")
        self.setAccessibleDescription(
            "Solte arquivos ou pastas aqui, ou pressione Enter para escolher"
        )

        self._compacto = False
        self._sob_arraste = False
        self.setMaximumHeight(ALTURA_GRANDE)
        self.setMinimumHeight(ALTURA_COMPACTA)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.SPACE["xl"], theme.SPACE["xl"], theme.SPACE["xl"], theme.SPACE["xl"]
        )
        layout.setSpacing(theme.SPACE["sm"])
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icone = QLabel()
        self._icone.setPixmap(icons.pixmap("upload", theme.COLOR["ink_soft"], 40))
        self._icone.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._titulo = QLabel("Solte seus arquivos aqui")
        self._titulo.setObjectName("DropZoneTitulo")
        self._titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._ajuda = QLabel("ou clique para escolher. Pastas entram inteiras.")
        self._ajuda.setObjectName("DropZoneAjuda")
        self._ajuda.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._icone)
        layout.addWidget(self._titulo)
        layout.addWidget(self._ajuda)

        self._animacao = QPropertyAnimation(self, b"maximumHeight", self)
        self._animacao.setDuration(theme.MOTION["normal"])
        self._animacao.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._pintar()

    # estado

    @property
    def compacto(self) -> bool:
        return self._compacto

    def definir_compacto(self, compacto: bool) -> None:
        """Alterna entre a versao grande e a faixa fina."""
        if compacto == self._compacto:
            return
        self._compacto = compacto
        alvo = ALTURA_COMPACTA if compacto else ALTURA_GRANDE

        for widget in (self._icone, self._ajuda):
            widget.setVisible(not compacto)
        self._titulo.setText(
            "Solte mais arquivos aqui" if compacto else "Solte seus arquivos aqui"
        )

        if self._animar():
            self._animacao.stop()
            self._animacao.setStartValue(self.maximumHeight())
            self._animacao.setEndValue(alvo)
            self._animacao.start()
        else:
            self.setMaximumHeight(alvo)

    def _animar(self) -> bool:
        """Respeita a preferencia de animacao do sistema, quando ela existe.

        Quem desligou animacao no Windows desligou por um motivo, as vezes
        enjoo com movimento. Nesse caso o valor final vai direto, sem
        transicao.

        O Qt nao expoe essa preferencia de forma estavel entre versoes, e
        o nome do metodo mudou mais de uma vez. Por isso a consulta e
        defensiva: se a versao instalada nao souber responder, animar e o
        padrao, porque e o comportamento que a maioria espera.
        """
        from PySide6.QtGui import QGuiApplication

        estilo = QGuiApplication.styleHints()
        consulta = getattr(estilo, "useHoverEffects", None)
        if consulta is None:
            return True
        try:
            return bool(consulta())
        except (AttributeError, TypeError):
            return True

    # aparencia

    def _pintar(self) -> None:
        borda = theme.COLOR["accent"] if self._sob_arraste else theme.COLOR["border_strong"]
        fundo = theme.COLOR["surface_alt"] if self._sob_arraste else theme.COLOR["surface"]
        self.setStyleSheet(
            f"#DropZone {{"
            f" border: 2px dashed {borda};"
            f" border-radius: {theme.RADIUS['lg']}px;"
            f" background: {fundo};"
            f"}}"
        )

    def _marcar_arraste(self, ativo: bool) -> None:
        if ativo != self._sob_arraste:
            self._sob_arraste = ativo
            self._pintar()

    # eventos de arraste

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

        caminhos = [
            Path(url.toLocalFile())
            for url in mime.urls()
            if url.isLocalFile() and url.toLocalFile()
        ]
        if not caminhos:
            evento.ignore()
            return

        evento.acceptProposedAction()
        self.arquivos_soltos.emit(caminhos)

    # clique e teclado

    def mouseReleaseEvent(self, evento: QMouseEvent) -> None:
        if evento.button() is Qt.MouseButton.LeftButton and self.rect().contains(
            evento.position().toPoint()
        ):
            self.clicada.emit()
        super().mouseReleaseEvent(evento)

    def keyPressEvent(self, evento) -> None:
        if evento.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicada.emit()
            evento.accept()
            return
        super().keyPressEvent(evento)
