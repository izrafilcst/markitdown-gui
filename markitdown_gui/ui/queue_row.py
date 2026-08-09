"""Uma linha da fila, da esquerda para a direita.

icone do formato, nome do arquivo em fonte mono, estado com icone e texto,
e o botao de acao, que muda conforme o estado.

Duas decisoes de acessibilidade estao codificadas aqui e travadas por
teste. A primeira: cor nunca e o unico indicador de estado, entao todo
estado carrega icone e texto alem da cor, por daltonismo. A segunda: item
em processamento mostra barra indeterminada, porque o markitdown nao
reporta progresso parcial e desenhar uma porcentagem inventada seria
mentir para o usuario sobre quanto falta.

O botao de acao e um so, que troca de papel, e nao tres botoes escondendo
e aparecendo. Isso mantem a posicao do alvo de clique estavel enquanto o
item muda de estado, o que importa para quem tem dificuldade motora.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..jobs.models import Estado, Item
from . import icons, theme

ALVO_MINIMO = 32

# Cada estado carrega icone, cor do texto e o papel do botao de acao.
# Manter os tres na mesma tabela evita que um deles seja esquecido quando
# um estado novo aparecer.
_ESTADOS = {
    Estado.PENDENTE: ("ampulheta", "ink_mute", "remover"),
    Estado.PROCESSANDO: ("repetir", "ink_soft", None),
    Estado.CONCLUIDO: ("check", "success_text", "abrir"),
    Estado.FALHOU: ("alerta", "danger_text", "repetir"),
    Estado.CANCELADO: ("x", "ink_mute", "remover"),
}

_ACOES = {
    "remover": ("lixeira", "Remover da fila"),
    "repetir": ("repetir", "Tentar converter de novo"),
    "abrir": ("abrir-externo", "Abrir o arquivo convertido"),
}


class LinhaDaFila(QWidget):
    """Um item da fila desenhado."""

    remover_pedido = Signal(str)
    repetir_pedido = Signal(str)
    abrir_pedido = Signal(str)
    detalhe_pedido = Signal(str)

    def __init__(self, item: Item, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LinhaDaFila")
        self.item_id = item.id
        self._acao_atual: str | None = None
        self._icone_estado = QIcon()

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(
            theme.SPACE["md"], theme.SPACE["sm"], theme.SPACE["md"], theme.SPACE["sm"]
        )
        raiz.setSpacing(theme.SPACE["md"])

        self._icone_formato = QLabel()
        self._icone_formato.setPixmap(
            icons.pixmap("arquivo", theme.COLOR["ink_soft"], 20)
        )

        meio = QVBoxLayout()
        meio.setSpacing(theme.SPACE["xs"])

        self._nome = QLabel()
        self._nome.setObjectName("LinhaNome")
        self._nome.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        linha_estado = QHBoxLayout()
        linha_estado.setSpacing(theme.SPACE["xs"])

        self._icone_estado_label = QLabel()
        self._estado = QLabel()
        self._estado.setObjectName("LinhaEstado")
        self._estado.setWordWrap(True)

        self.botao_detalhe = QPushButton("Ver detalhes")
        self.botao_detalhe.setObjectName("BotaoDiscreto")
        self.botao_detalhe.setMinimumSize(ALVO_MINIMO * 3, ALVO_MINIMO)
        self.botao_detalhe.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_detalhe.clicked.connect(
            lambda: self.detalhe_pedido.emit(self.item_id)
        )

        linha_estado.addWidget(self._icone_estado_label)
        linha_estado.addWidget(self._estado, 1)
        linha_estado.addWidget(self.botao_detalhe)

        self._barra = QProgressBar()
        self._barra.setRange(0, 0)          # indeterminada, de proposito
        self._barra.setTextVisible(False)
        self._barra.setFixedHeight(4)
        self._barra.setAccessibleName("Convertendo, aguarde")

        meio.addWidget(self._nome)
        meio.addLayout(linha_estado)
        meio.addWidget(self._barra)

        self.botao_acao = QPushButton()
        self.botao_acao.setMinimumSize(ALVO_MINIMO, ALVO_MINIMO)
        self.botao_acao.setIconSize(QSize(18, 18))
        self.botao_acao.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_acao.clicked.connect(self._ao_clicar_acao)

        raiz.addWidget(self._icone_formato)
        raiz.addLayout(meio, 1)
        raiz.addWidget(self.botao_acao)

        self.atualizar(item)

    # leitura, usada pelos testes e pela janela principal

    def texto_do_nome(self) -> str:
        return self._nome.text()

    def texto_de_estado(self) -> str:
        return self._estado.text()

    def icone_de_estado(self) -> QIcon:
        return self._icone_estado

    def barra_de_progresso(self) -> QProgressBar:
        return self._barra

    def acao_visivel(self) -> str | None:
        return self._acao_atual

    # atualizacao

    def atualizar(self, item: Item) -> None:
        """Redesenha a linha para o estado atual do item.

        A linha e reusada e nao recriada, para nao perder foco de teclado
        nem posicao de rolagem quando o estado muda no meio de um lote.
        """
        self.item_id = item.id
        self._nome.setText(item.nome)
        self._nome.setToolTip(str(item.origem))

        nome_icone, token_cor, acao = _ESTADOS[item.estado]

        # Texto de estado: rotulo sempre, mais a mensagem quando houver.
        # O rotulo nunca some, porque e ele que o teste de daltonismo cobra.
        texto = item.estado.rotulo
        if item.mensagem:
            texto = f"{texto}: {item.mensagem}"
        self._estado.setText(texto)
        self._estado.setStyleSheet(f"color: {theme.COLOR[token_cor]};")

        self._icone_estado = icons.icone(nome_icone, theme.COLOR[token_cor], 16)
        self._icone_estado_label.setPixmap(
            icons.pixmap(nome_icone, theme.COLOR[token_cor], 16)
        )

        self._barra.setVisible(item.estado is Estado.PROCESSANDO)
        self.botao_detalhe.setVisible(bool(item.detalhe))

        self._acao_atual = acao
        if acao is None:
            self.botao_acao.setVisible(False)
            self.botao_acao.setIcon(QIcon())
            self.botao_acao.setAccessibleName("")
        else:
            nome_svg, rotulo = _ACOES[acao]
            self.botao_acao.setVisible(True)
            self.botao_acao.setIcon(icons.icone(nome_svg, theme.COLOR["ink"]))
            self.botao_acao.setAccessibleName(f"{rotulo}: {item.nome}")
            self.botao_acao.setToolTip(rotulo)

        self.setAccessibleName(f"{item.nome}, {texto}")

    def _ao_clicar_acao(self) -> None:
        if self._acao_atual == "remover":
            self.remover_pedido.emit(self.item_id)
        elif self._acao_atual == "repetir":
            self.repetir_pedido.emit(self.item_id)
        elif self._acao_atual == "abrir":
            self.abrir_pedido.emit(self.item_id)
