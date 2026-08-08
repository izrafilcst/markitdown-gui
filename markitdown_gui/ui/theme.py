"""Tokens de design e folha de estilo do app.

Este modulo e a unica fonte de cor literal do projeto. Qualquer outro
arquivo que precise de cor importa `theme.COLOR`.

A paleta veio do cliente (Sky Aqua, Snow, Mint Leaf, Pearl Aqua) e foi
medida contra WCAG antes de ser congelada. O resultado da medicao importa:
as cinco cores originais falham como cor de texto, inclusive com branco
por cima. Elas sao cores de superficie. O token `ink` existe para resolver
isso sem sair da familia de matiz.

`PARES_AUDITADOS` transforma essa medicao em teste, em `tests/test_contraste.py`.
"""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtWidgets import QApplication


COLOR = {
    # superficies
    "bg":            "#FFFBFA",  # Snow, fundo da janela
    "surface":       "#FFFFFF",  # cartoes e linhas da fila
    "surface_alt":   "#EAF6F5",  # hover de linha, zona de arraste em repouso
    "border":        "#D6E7E6",  # divisorias decorativas
    "border_strong": "#8BD7D2",  # Pearl Aqua, borda da zona de arraste

    # tinta (todas medidas sobre Snow)
    "ink":       "#0B2B33",  # 14.52:1  titulo e texto principal
    "ink_soft":  "#33565C",  #  7.78:1  texto secundario
    "ink_mute":  "#5A7A80",  #  4.51:1  piso absoluto, nao clarear mais

    # acao
    "primary":       "#00BD9D",  # Mint Leaf, preenchimento do botao
    "primary_hover": "#00A88C",  # Ink continua em 4.96:1
    "primary_press": "#00A489",  # Ink em 4.74:1, nao escurecer alem disto
    "on_primary":    "#0B2B33",  # Ink. NUNCA branco: branco da 2.40:1

    # acento, apenas preenchimento e nunca texto
    "accent":       "#49C6E5",  # Sky Aqua
    "accent_light": "#54DEFD",
    "accent_soft":  "#8BD7D2",  # Pearl Aqua

    # foco: Sky Aqua puro falha (1.95:1), entao usa-se a versao profunda
    "focus": "#0E6A80",  # 6.02:1

    # estados: versao de preenchimento e versao de texto sao diferentes
    "success":      "#00BD9D",  "success_text": "#00785F",  # 5.30:1
    "warning":      "#F5B301",  "warning_text": "#A15C00",  # 5.05:1
    "danger":       "#E5533D",  "danger_text":  "#B3261E",  # 6.36:1
}

SPACE  = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "2xl": 32}
RADIUS = {"sm": 6, "md": 10, "lg": 14, "pill": 999}
MOTION = {"fast": 150, "normal": 250}   # milissegundos
FONT   = {
    "ui":   ("Inter", "Segoe UI Variable Text", "Segoe UI", "Arial"),
    "mono": ("JetBrains Mono", "Cascadia Mono", "Consolas", "monospace"),
}
SIZE = {"xs": 11, "sm": 12, "md": 13, "lg": 15, "xl": 20, "2xl": 28}


PARES_AUDITADOS = [
    # (token de frente, token de fundo, minimo WCAG)
    ("ink",          "bg",       4.5),
    ("ink_soft",     "bg",       4.5),
    ("ink_mute",     "bg",       4.5),
    ("ink",          "surface",  4.5),
    ("ink",          "surface_alt", 4.5),
    ("on_primary",   "primary",       4.5),
    ("on_primary",   "primary_hover", 4.5),
    ("on_primary",   "primary_press", 4.5),
    ("ink",          "accent",      4.5),
    ("ink",          "accent_soft", 4.5),
    ("success_text", "bg",  4.5),
    ("warning_text", "bg",  4.5),
    ("danger_text",  "bg",  4.5),
    ("focus",        "bg",  3.0),   # anel de foco e elemento nao-textual
]


PASTA_FONTES = Path(__file__).resolve().parent.parent / "resources" / "fonts"

# Familias registradas por carregar_fontes, na ordem em que entraram.
_FAMILIAS_EMBARCADAS: list[str] = []
_FONTES_CARREGADAS = False


def _lista_css(papel: str) -> str:
    """Cadeia de fallback de fonte no formato que o QSS entende."""
    return ", ".join(f'"{nome}"' for nome in FONT[papel])


_VARS: dict[str, object] = {}
_VARS.update(COLOR)
_VARS.update({f"space_{chave}": valor for chave, valor in SPACE.items()})
_VARS.update({f"radius_{chave}": valor for chave, valor in RADIUS.items()})
_VARS.update({f"size_{chave}": valor for chave, valor in SIZE.items()})
_VARS["font_ui"] = _lista_css("ui")
_VARS["font_mono"] = _lista_css("mono")

# O template usa ${token} em vez de f-string porque o QSS e cheio de chaves
# e escapar todas elas seria uma fonte silenciosa de erro.
_QSS = Template("""
/* Base. Toda cor vem de theme.COLOR, nenhuma e escrita a mao aqui. */
QWidget {
    background-color: ${bg};
    color: ${ink};
    font-family: ${font_ui};
    font-size: ${size_md}px;
}

QMainWindow {
    background-color: ${bg};
}

QMainWindow::separator {
    background-color: ${border};
    width: 1px;
    height: 1px;
}

/* Rotulos. O papel e uma propriedade dinamica, nao uma cor solta. */
QLabel {
    background: transparent;
    color: ${ink};
}
QLabel[papel="titulo"] {
    font-size: ${size_2xl}px;
    font-weight: 600;
}
QLabel[papel="secao"] {
    font-size: ${size_lg}px;
    font-weight: 600;
}
QLabel[papel="secundario"] {
    color: ${ink_soft};
    font-size: ${size_sm}px;
}
QLabel[papel="mudo"] {
    color: ${ink_mute};
    font-size: ${size_sm}px;
}
QLabel[papel="mono"] {
    font-family: ${font_mono};
}
QLabel[papel="sucesso"] { color: ${success_text}; }
QLabel[papel="alerta"]  { color: ${warning_text}; }
QLabel[papel="erro"]    { color: ${danger_text}; }

/* Botao secundario, que e o padrao quando nada e declarado. */
QPushButton {
    background-color: ${surface};
    color: ${ink};
    border: 1px solid ${border};
    border-radius: ${radius_md}px;
    padding: ${space_sm}px ${space_lg}px;
    min-height: 32px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: ${surface_alt};
    border-color: ${border_strong};
}
QPushButton:pressed {
    background-color: ${accent_soft};
}
QPushButton:disabled {
    color: ${ink_mute};
    background-color: ${surface};
    border-color: ${border};
}

/* Botao primario. O texto e ink por contrato: branco sobre Mint Leaf
   da 2.40:1 e reprovaria. */
QPushButton[variante="primario"] {
    background-color: ${primary};
    color: ${on_primary};
    border: 1px solid ${primary};
    font-weight: 600;
}
QPushButton[variante="primario"]:hover {
    background-color: ${primary_hover};
    border-color: ${primary_hover};
}
QPushButton[variante="primario"]:pressed {
    background-color: ${primary_press};
    border-color: ${primary_press};
}
QPushButton[variante="primario"]:disabled {
    background-color: ${surface_alt};
    color: ${ink_mute};
    border-color: ${border};
}

/* Botao discreto, usado nas acoes de linha da fila. */
QPushButton[variante="discreto"] {
    background: transparent;
    color: ${ink_soft};
    border: 1px solid transparent;
    padding: ${space_xs}px ${space_sm}px;
    min-width: 32px;
    min-height: 32px;
}
QPushButton[variante="discreto"]:hover {
    background-color: ${surface_alt};
    color: ${ink};
}
QPushButton[variante="discreto"]:pressed {
    background-color: ${accent_soft};
    color: ${ink};
}
QPushButton[variante="discreto"]:disabled {
    color: ${ink_mute};
    background: transparent;
}

QPushButton[variante="perigo"] {
    background: transparent;
    color: ${danger_text};
    border: 1px solid ${border};
}
QPushButton[variante="perigo"]:hover {
    background-color: ${surface_alt};
    border-color: ${danger};
}

QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: ${radius_sm}px;
    padding: ${space_xs}px;
    min-width: 32px;
    min-height: 32px;
}
QToolButton:hover {
    background-color: ${surface_alt};
}
QToolButton:pressed {
    background-color: ${accent_soft};
}

/* Lista da fila. */
QListWidget {
    background-color: ${surface};
    border: 1px solid ${border};
    border-radius: ${radius_lg}px;
    padding: ${space_xs}px;
    outline: none;
}
QListWidget::item {
    background-color: ${surface};
    border: 1px solid transparent;
    border-radius: ${radius_md}px;
    padding: ${space_sm}px;
    margin: ${space_xs}px 0px;
    color: ${ink};
    min-height: 32px;
}
QListWidget::item:hover {
    background-color: ${surface_alt};
    border-color: ${border};
}
QListWidget::item:selected {
    background-color: ${surface_alt};
    border-color: ${border_strong};
    color: ${ink};
}
QListWidget::item:selected:active {
    background-color: ${accent_soft};
    color: ${ink};
}

/* Campos de texto. */
QLineEdit {
    background-color: ${surface};
    color: ${ink};
    border: 1px solid ${border};
    border-radius: ${radius_sm}px;
    padding: ${space_sm}px ${space_md}px;
    min-height: 32px;
    selection-background-color: ${accent_soft};
    selection-color: ${ink};
}
QLineEdit:hover {
    border-color: ${border_strong};
}
QLineEdit:read-only {
    background-color: ${surface_alt};
    color: ${ink_soft};
}
QLineEdit:disabled {
    background-color: ${surface_alt};
    color: ${ink_mute};
}
QLineEdit[papel="caminho"] {
    font-family: ${font_mono};
    font-size: ${size_sm}px;
}

QPlainTextEdit, QTextEdit {
    background-color: ${surface};
    color: ${ink};
    border: 1px solid ${border};
    border-radius: ${radius_md}px;
    padding: ${space_sm}px;
    font-family: ${font_mono};
    font-size: ${size_sm}px;
    selection-background-color: ${accent_soft};
    selection-color: ${ink};
}

/* Barra de rolagem discreta, no lugar da barra nativa do Windows. */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: ${border_strong};
    border-radius: 5px;
    min-height: ${space_2xl}px;
}
QScrollBar::handle:vertical:hover {
    background-color: ${accent};
}
QScrollBar::handle:vertical:pressed {
    background-color: ${focus};
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: ${border_strong};
    border-radius: 5px;
    min-width: ${space_2xl}px;
}
QScrollBar::handle:horizontal:hover {
    background-color: ${accent};
}
QScrollBar::handle:horizontal:pressed {
    background-color: ${focus};
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
    background: transparent;
    border: none;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}

QScrollArea {
    background-color: ${bg};
    border: none;
}

/* Dica. Fundo ink com texto Snow da 14.52:1. */
QToolTip {
    background-color: ${ink};
    color: ${bg};
    border: 1px solid ${ink};
    border-radius: ${radius_sm}px;
    padding: ${space_xs}px ${space_sm}px;
    font-size: ${size_sm}px;
}

/* Progresso. O item em conversao usa modo indeterminado, porque o
   markitdown nao reporta progresso parcial e fingir seria mentira. */
QProgressBar {
    background-color: ${surface_alt};
    border: 1px solid ${border};
    border-radius: ${radius_sm}px;
    height: 8px;
    text-align: center;
    color: ${ink};
    font-size: ${size_xs}px;
}
QProgressBar::chunk {
    background-color: ${primary};
    border-radius: ${radius_sm}px;
}
QProgressBar[estado="erro"]::chunk {
    background-color: ${danger};
}

QStatusBar {
    background-color: ${bg};
    color: ${ink_soft};
    border-top: 1px solid ${border};
}
QStatusBar::item {
    border: none;
}

QMenu {
    background-color: ${surface};
    border: 1px solid ${border};
    border-radius: ${radius_md}px;
    padding: ${space_xs}px;
}
QMenu::item {
    padding: ${space_sm}px ${space_lg}px;
    border-radius: ${radius_sm}px;
    color: ${ink};
}
QMenu::item:selected {
    background-color: ${surface_alt};
}
QMenu::separator {
    height: 1px;
    background-color: ${border};
    margin: ${space_xs}px 0px;
}

QCheckBox, QRadioButton {
    background: transparent;
    color: ${ink};
    spacing: ${space_sm}px;
    min-height: 32px;
}

QFrame[papel="cartao"] {
    background-color: ${surface};
    border: 1px solid ${border};
    border-radius: ${radius_lg}px;
}
QFrame[papel="divisoria"] {
    background-color: ${border};
    max-height: 1px;
    border: none;
}

QDialog {
    background-color: ${bg};
}

/* Anel de foco. Precisa existir em todo elemento focavel, porque
   navegacao por teclado sem foco visivel e navegacao as cegas.
   Sky Aqua puro reprova em 1.95:1, por isso o token focus e a versao
   profunda, que mede 6.02:1 sobre Snow. */
QPushButton:focus,
QToolButton:focus,
QLineEdit:focus,
QPlainTextEdit:focus,
QTextEdit:focus,
QListWidget:focus,
QComboBox:focus,
QCheckBox:focus,
QRadioButton:focus,
QAbstractSpinBox:focus,
QTabBar::tab:focus,
QScrollBar:focus {
    border: 2px solid ${focus};
}
QListWidget::item:focus {
    border: 2px solid ${focus};
}
QFrame[papel="cartao"]:focus {
    border: 2px solid ${focus};
}
""")


def carregar_fontes() -> None:
    """Registra fontes embarcadas de resources/fonts, se existirem.

    O app nao depende delas: a cadeia de fallback em FONT resolve para
    Segoe UI no Windows. Chamar mais de uma vez e barato, porque a
    segunda chamada nao faz nada.
    """
    global _FONTES_CARREGADAS

    if _FONTES_CARREGADAS:
        return
    _FONTES_CARREGADAS = True

    if not PASTA_FONTES.is_dir():
        return

    from PySide6.QtGui import QFontDatabase

    arquivos = sorted(
        caminho
        for caminho in PASTA_FONTES.iterdir()
        if caminho.suffix.lower() in (".ttf", ".otf")
    )
    for caminho in arquivos:
        indice = QFontDatabase.addApplicationFont(str(caminho))
        if indice == -1:
            continue
        for nome in QFontDatabase.applicationFontFamilies(indice):
            if nome not in _FAMILIAS_EMBARCADAS:
                _FAMILIAS_EMBARCADAS.append(nome)


def familia(papel: str) -> str:
    """Primeira fonte de FONT[papel] realmente disponivel no sistema.

    Cai no ultimo nome da tupla quando nenhuma esta instalada, porque esse
    ultimo nome e sempre um generico que o proprio Qt resolve.
    """
    candidatas = FONT[papel]

    try:
        from PySide6.QtGui import QFontDatabase

        instaladas = set(QFontDatabase.families())
    except Exception:
        # Sem QGuiApplication viva nao da para consultar o sistema.
        return candidatas[0]

    for nome in candidatas:
        if nome in _FAMILIAS_EMBARCADAS or nome in instaladas:
            return nome
    return candidatas[-1]


def qss() -> str:
    """Folha de estilo completa do app, montada a partir dos tokens."""
    return _QSS.substitute(_VARS)


def aplicar(app: "QApplication") -> None:
    """carregar_fontes + setFont + setStyleSheet. Chamado uma vez no main."""
    from PySide6.QtGui import QFont

    carregar_fontes()

    fonte = QFont(familia("ui"))
    fonte.setPixelSize(SIZE["md"])
    app.setFont(fonte)
    app.setStyleSheet(qss())
