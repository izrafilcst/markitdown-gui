"""A aba de conversoes recentes.

Mostra o que ja foi convertido, quando, quanto texto saiu e o que deu
errado quando deu. Le do `core.historico`, que e Python puro, e nao guarda
estado proprio: a fonte da verdade e o banco, e a aba so desenha.

Duas decisoes de produto moram aqui.

A primeira: **abrir o convertido a partir do historico so funciona se o
arquivo ainda existir.** Ele pode ter sido apagado, movido ou renomeado
desde a conversao, e nesse caso a aba diz isso em vez de abrir o
gerenciador de arquivos numa pasta vazia.

A segunda: **existe um botao de apagar o historico inteiro.** O app grava
nome de arquivo do usuario, e quem guarda dado de alguem precisa oferecer
o botao de apagar. Nao adianta ser local se nao for reversivel.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.historico import Historico, Registro
from . import icons, theme

ALVO_MINIMO = 32
ALTURA_DA_LINHA = 64
LIMITE = 200

# Espaco que `QListWidget::item` consome no QSS: borda, padding e
# margem, em cima e embaixo. O item precisa reservar isso ALEM da
# altura da linha, senao o widget transborda a caixa e o texto de
# baixo some. E a mesma conta de queue_view.py, pela mesma razao.
_BORDA_DO_ITEM = 1
CHROME_VERTICAL = 2 * (_BORDA_DO_ITEM + theme.SPACE["sm"] + theme.SPACE["xs"])


class LinhaRecente(QWidget):
    """Uma conversao passada, desenhada."""

    def __init__(self, registro: Registro, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.registro = registro
        self.setFixedHeight(ALTURA_DA_LINHA)

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(
            theme.SPACE["md"], theme.SPACE["sm"], theme.SPACE["md"], theme.SPACE["sm"]
        )
        raiz.setSpacing(theme.SPACE["md"])

        self._token = "success_text" if registro.sucesso else "danger_text"
        self._selecionada = False
        token = self._token
        self._marca = QLabel()
        marca = self._marca
        marca.setPixmap(
            icons.pixmap(
                "check" if registro.sucesso else "alerta", theme.COLOR[token], 18
            )
        )

        meio = QVBoxLayout()
        meio.setSpacing(theme.SPACE["xs"])

        self._nome_completo = registro.origem.name
        self._nome = QLabel(self._nome_completo)
        self._nome.setObjectName("LinhaNome")
        self._nome.setToolTip(str(registro.origem))
        # Sem isto o rotulo exige a largura do nome inteiro e a linha
        # transborda a lista, em vez de o nome encolher.
        self._nome.setMinimumWidth(0)
        self._nome.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )

        self._detalhe = QLabel(self._resumo())
        self._detalhe.setObjectName("LinhaEstado")
        self._detalhe.setStyleSheet(f"color: {theme.COLOR[token]};")
        self._detalhe.setToolTip(str(registro.destino))

        meio.addWidget(self._nome)
        meio.addWidget(self._detalhe)

        raiz.addWidget(marca, 0, Qt.AlignmentFlag.AlignTop)
        raiz.addLayout(meio, 1)

        self.setAccessibleName(f"{registro.origem.name}, {self._resumo()}")

    def _resumo(self) -> str:
        partes = [self.registro.quando_legivel()]
        if self.registro.sucesso:
            partes.append(self.registro.tamanho_legivel())
        else:
            partes.append(self.registro.mensagem or "falhou")
        return "  |  ".join(partes)

    def texto(self) -> str:
        return f"{self._nome.text()}  {self._detalhe.text()}"

    def texto_do_nome(self) -> str:
        return self._nome.text()

    def nome_completo(self) -> str:
        return self._nome_completo

    def cor_do_texto(self) -> str:
        """Token de cor em uso no momento, para a interface e para o teste."""
        return theme.COLOR["on_accent" if self._selecionada else self._token]

    def definir_selecionada(self, selecionada: bool) -> None:
        """Recolore a linha quando ela entra ou sai da selecao.

        Widget colocado com setItemWidget NAO herda o estilo de
        `QListWidget::item:selected` do QSS: ele e um widget filho, e nao
        o item. Sem esta chamada, o texto continua com a cor do estado
        sobre o fundo claro da selecao, o que mede 1.06:1 no tema escuro.
        """
        if selecionada == self._selecionada:
            return
        self._selecionada = selecionada
        cor = self.cor_do_texto()
        self._detalhe.setStyleSheet(f"color: {cor};")
        self._nome.setStyleSheet(f"color: {cor};")
        self._marca.setPixmap(
            icons.pixmap(
                "check" if self.registro.sucesso else "alerta", cor, 18
            )
        )

    def _encurtar_nome(self) -> None:
        """Encaixa o nome na largura disponivel, cortando pelo meio.

        Pelo meio para preservar a extensao, que e o que identifica o
        arquivo numa lista de conversoes.
        """
        largura = self._nome.width()
        if largura <= 0:
            self._nome.setText(self._nome_completo)
            return
        metrica = QFontMetrics(self._nome.font())
        self._nome.setText(
            metrica.elidedText(
                self._nome_completo, Qt.TextElideMode.ElideMiddle, largura
            )
        )

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self._encurtar_nome()

    def sizeHint(self) -> QSize:
        return QSize(super().sizeHint().width(), ALTURA_DA_LINHA)


class AbaRecentes(QWidget):
    """Lista das conversoes ja feitas."""

    abrir_pedido = Signal(object)   # Path do arquivo convertido

    def __init__(
        self, historico: Historico | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.historico = historico if historico is not None else Historico()
        self._linhas: list[LinhaRecente] = []
        self._erro = ""

        raiz = QVBoxLayout(self)
        # As mesmas margens da aba da fila. Com zero, o rodape encosta na
        # borda e o ultimo botao sai cortado pela lateral da janela.
        raiz.setContentsMargins(
            theme.SPACE["lg"], theme.SPACE["lg"], theme.SPACE["lg"], theme.SPACE["lg"]
        )
        raiz.setSpacing(theme.SPACE["md"])

        self.lista = QListWidget()
        self.lista.setObjectName("ListaRecentes")
        self.lista.setAccessibleName("Conversoes recentes")
        self.lista.itemDoubleClicked.connect(self._ao_clicar_duas_vezes)
        self.lista.itemSelectionChanged.connect(self._ao_mudar_selecao)

        self.rotulo_vazio = QLabel(self.mensagem_de_vazio())
        self.rotulo_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_vazio.setWordWrap(True)
        self.rotulo_vazio.setStyleSheet(f"color: {theme.COLOR['ink_mute']};")

        rodape = QHBoxLayout()
        rodape.setSpacing(theme.SPACE["sm"])

        self.rotulo_total = QLabel("")
        self.rotulo_total.setStyleSheet(f"color: {theme.COLOR['ink_soft']};")

        self.botao_abrir = QPushButton("Abrir convertido")
        self.botao_abrir.setMinimumSize(150, ALVO_MINIMO)
        self.botao_abrir.setIcon(icons.icone("abrir-externo", theme.COLOR["ink"]))
        self.botao_abrir.clicked.connect(self._abrir_selecionado)

        self.botao_limpar = QPushButton("Apagar historico")
        self.botao_limpar.setMinimumSize(150, ALVO_MINIMO)
        self.botao_limpar.setIcon(icons.icone("lixeira", theme.COLOR["ink"]))
        self.botao_limpar.clicked.connect(self._confirmar_limpeza)

        rodape.addWidget(self.rotulo_total, 1)
        rodape.addWidget(self.botao_abrir)
        rodape.addWidget(self.botao_limpar)

        raiz.addWidget(self.rotulo_vazio)
        raiz.addWidget(self.lista, 1)
        raiz.addLayout(rodape)

        self.atualizar()

    # ------------------------------------------------------------ dados

    def atualizar(self) -> None:
        """Recarrega do banco. A aba nao guarda estado proprio."""
        self.lista.clear()
        self._linhas.clear()

        for registro in self.historico.recentes(limite=LIMITE):
            linha = LinhaRecente(registro)
            casca = QListWidgetItem(self.lista)
            pedido = linha.sizeHint()
            casca.setSizeHint(
                QSize(pedido.width(), pedido.height() + CHROME_VERTICAL)
            )
            self.lista.addItem(casca)
            self.lista.setItemWidget(casca, linha)
            self._linhas.append(linha)

        tem = bool(self._linhas)
        self.lista.setVisible(tem)
        self.rotulo_vazio.setVisible(not tem)
        self.botao_abrir.setEnabled(tem)
        self.botao_limpar.setEnabled(tem)
        self.rotulo_total.setText(
            f"{len(self._linhas)} conversoes guardadas" if tem else ""
        )

    # ------------------------------------------------ leitura para teste

    def linha_widget(self, indice: int) -> LinhaRecente:
        return self._linhas[indice]

    def quantidade_exibida(self) -> int:
        return len(self._linhas)

    def nomes_exibidos(self) -> list[str]:
        return [linha.registro.origem.name for linha in self._linhas]

    def texto_da_linha(self, indice: int) -> str:
        return self._linhas[indice].texto()

    def mensagem_de_vazio(self) -> str:
        return (
            "Nenhuma conversao ainda.\n"
            "O que voce converter aparece aqui, com data e hora."
        )

    def mensagem_de_erro(self) -> str:
        return self._erro

    # ---------------------------------------------------------- comandos

    def abrir_linha(self, indice: int) -> None:
        """Pede para abrir o convertido daquela linha, se ele ainda existir."""
        self._erro = ""
        if indice < 0 or indice >= len(self._linhas):
            return
        destino = self._linhas[indice].registro.destino
        if not destino or not destino.exists():
            self._erro = (
                "O arquivo convertido nao esta mais no lugar. "
                "Ele pode ter sido movido, renomeado ou apagado."
            )
            self.rotulo_total.setText(self._erro)
            return
        self.abrir_pedido.emit(destino)

    def limpar_tudo(self) -> None:
        self.historico.limpar()
        self.atualizar()

    # ------------------------------------------------------------ apoio

    def _ao_mudar_selecao(self) -> None:
        """Avisa cada linha se ela esta selecionada ou nao.

        Feito no widget e nao so no QSS porque widget embutido com
        setItemWidget nao recebe o estado de selecao do item.
        """
        # Segue a SELECAO, e nao a linha atual. No Qt os dois estados sao
        # diferentes: `currentRow` e o foco de teclado e sobrevive a um
        # clearSelection. Quem pinta o fundo no QSS e `:selected`, entao
        # seguir outra coisa deixaria a cor do texto fora de sincronia com
        # o fundo, que e justamente o defeito que estamos consertando.
        selecionadas = {self.lista.row(c) for c in self.lista.selectedItems()}
        for indice, linha in enumerate(self._linhas):
            linha.definir_selecionada(indice in selecionadas)

    def _linha_selecionada(self) -> int:
        return self.lista.currentRow()

    def _abrir_selecionado(self) -> None:
        indice = self._linha_selecionada()
        self.abrir_linha(indice if indice >= 0 else 0)

    def _ao_clicar_duas_vezes(self, casca: QListWidgetItem) -> None:
        self.abrir_linha(self.lista.row(casca))

    def _confirmar_limpeza(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        resposta = QMessageBox.question(
            self,
            "Apagar historico",
            "Isto apaga a lista de conversoes recentes deste computador.\n\n"
            "Os arquivos convertidos NAO sao apagados, so o registro de que "
            "eles foram convertidos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            self.limpar_tudo()
