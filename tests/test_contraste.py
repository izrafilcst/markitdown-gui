"""A acessibilidade do app e verificada por maquina, nao por opiniao.

A paleta que o cliente forneceu (Sky Aqua, Snow, Mint Leaf, Pearl Aqua) e
uma paleta de superficies: nenhuma das cinco cores passa 4.5:1 como texto
sobre a Snow, e texto branco sobre elas tambem falha. Por isso existe o
token `ink`. Este teste impede que alguem "simplifique" isso depois.
"""
import pytest

from markitdown_gui.ui import theme


def luminancia(hexa: str) -> float:
    hexa = hexa.lstrip("#")
    canais = []
    for i in (0, 2, 4):
        c = int(hexa[i:i + 2], 16) / 255
        canais.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = canais
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razao(a: str, b: str) -> float:
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@pytest.mark.parametrize("frente,fundo,minimo", theme.PARES_AUDITADOS)
def test_par_passa_wcag(frente, fundo, minimo):
    obtido = razao(theme.COLOR[frente], theme.COLOR[fundo])
    assert obtido >= minimo, (
        f"{frente} sobre {fundo} da {obtido:.2f}:1, precisa de {minimo}:1"
    )


def test_texto_do_botao_primario_nao_e_branco():
    """Branco sobre Mint Leaf da 2.40:1. O contrato manda usar ink."""
    assert theme.COLOR["on_primary"].upper() not in ("#FFF", "#FFFFFF")
    assert razao(theme.COLOR["on_primary"], theme.COLOR["primary"]) >= 4.5


def test_qss_nao_esta_vazio():
    assert len(theme.qss()) > 500


def test_qss_nao_tem_travessao():
    assert "—" not in theme.qss()
    assert "–" not in theme.qss()


# ------------------------------------------------------------ tema escuro

def test_as_duas_paletas_tem_os_mesmos_tokens():
    """Um token que existe so num tema vira KeyError na hora errada."""
    claros = set(theme.PALETA_CLARA)
    escuros = set(theme.PALETA_ESCURA)
    assert claros == escuros, (
        f"so no claro: {claros - escuros}; so no escuro: {escuros - claros}"
    )


@pytest.mark.parametrize("tema", ["claro", "escuro"])
@pytest.mark.parametrize("frente,fundo,minimo", theme.PARES_AUDITADOS)
def test_par_passa_wcag_nos_dois_temas(tema, frente, fundo, minimo):
    """Acessibilidade nao pode valer so no tema claro."""
    paleta = theme.PALETA_CLARA if tema == "claro" else theme.PALETA_ESCURA
    obtido = razao(paleta[frente], paleta[fundo])
    assert obtido >= minimo, (
        f"[{tema}] {frente} sobre {fundo} da {obtido:.2f}:1, precisa de {minimo}:1"
    )


def test_texto_sobre_accent_e_escuro_nos_dois_temas():
    """No tema escuro o ink e claro, e o accent tambem.

    Reusar `ink` como texto sobre accent funcionava no tema claro e
    reprovaria no escuro, com 1.77:1. Por isso existe `on_accent`, que e
    escuro nos dois temas. No tema claro ele vale exatamente o mesmo que
    `ink`, entao a auditoria original nao mudou de numero.
    """
    assert theme.PALETA_CLARA["on_accent"] == theme.PALETA_CLARA["ink"]
    for paleta in (theme.PALETA_CLARA, theme.PALETA_ESCURA):
        assert razao(paleta["on_accent"], paleta["accent"]) >= 4.5


def test_tema_claro_nao_mudou_de_valor():
    """Os tokens auditados do tema claro sao contrato congelado."""
    congelado = {
        "bg": "#FFFBFA", "surface": "#FFFFFF", "surface_alt": "#EAF6F5",
        "ink": "#0B2B33", "ink_soft": "#33565C", "ink_mute": "#5A7A80",
        "primary": "#00BD9D", "primary_hover": "#00A88C",
        "primary_press": "#00A489", "on_primary": "#0B2B33",
        "accent": "#49C6E5", "accent_soft": "#8BD7D2", "focus": "#0E6A80",
        "success_text": "#00785F", "warning_text": "#A15C00",
        "danger_text": "#B3261E",
    }
    for token, valor in congelado.items():
        assert theme.PALETA_CLARA[token].upper() == valor.upper()


def test_definir_tema_troca_as_cores_no_lugar():
    """A troca precisa acontecer DENTRO do dicionario, nao rebindando.

    Todo modulo de interface faz `from . import theme` e le `theme.COLOR`.
    Se `definir_tema` trocasse a referencia, quem ja tivesse guardado o
    dicionario antigo continuaria pintando com as cores do tema anterior.
    """
    original = theme.COLOR
    try:
        theme.definir_tema("escuro")
        assert theme.COLOR is original, "o dicionario foi trocado de identidade"
        assert theme.COLOR["bg"] == theme.PALETA_ESCURA["bg"]
        assert theme.tema_atual() == "escuro"

        theme.definir_tema("claro")
        assert theme.COLOR["bg"] == theme.PALETA_CLARA["bg"]
        assert theme.tema_atual() == "claro"
    finally:
        theme.definir_tema("claro")


def test_tema_desconhecido_falha_alto():
    with pytest.raises(ValueError):
        theme.definir_tema("roxo")


def test_qss_acompanha_o_tema():
    try:
        theme.definir_tema("claro")
        folha_clara = theme.qss()
        theme.definir_tema("escuro")
        folha_escura = theme.qss()

        assert theme.PALETA_CLARA["bg"] in folha_clara
        assert theme.PALETA_ESCURA["bg"] in folha_escura
        assert folha_clara != folha_escura
    finally:
        theme.definir_tema("claro")


def test_tema_do_sistema_responde_algo_valido(qapp):
    assert theme.tema_do_sistema() in ("claro", "escuro")


# ------------------------------------------------- selecao na lista

# Todo texto que pode aparecer numa linha selecionada. O fundo da selecao
# ativa e `accent_soft`, que e uma cor CLARA nos dois temas, entao texto
# claro por cima some. No tema escuro a medicao dava 1.01:1 para
# `ink_soft`, ou seja, invisivel.
# Cores de estado que aparecem na linha. Nenhuma delas serve como texto
# sobre a selecao, em nenhum dos dois temas.
TOKENS_DE_ESTADO = ["success_text", "danger_text", "warning_text"]


@pytest.mark.parametrize("tema", ["claro", "escuro"])
def test_texto_em_linha_selecionada_passa_wcag(tema):
    """Selecionar uma linha nao pode apagar o texto dela.

    A regra que resolve: sobre `accent_soft` o texto e sempre `on_accent`,
    que e escuro nos dois temas. E a mesma regra que ja vale para qualquer
    preenchimento de acento, so que agora aplicada tambem a selecao.
    """
    paleta = theme.PALETA_CLARA if tema == "claro" else theme.PALETA_ESCURA
    obtido = razao(paleta["on_accent"], paleta["accent_soft"])
    assert obtido >= 4.5, f"[{tema}] texto selecionado da {obtido:.2f}:1"


@pytest.mark.parametrize("tema", ["claro", "escuro"])
@pytest.mark.parametrize("token", TOKENS_DE_ESTADO)
def test_cor_de_estado_nao_serve_sobre_a_selecao(tema, token):
    """Documenta por que a linha precisa recolorir, e nao so herdar.

    Se alguma destas passasse, daria para manter a cor do estado quando a
    linha e selecionada. Nenhuma passa em nenhum dos dois temas, entao
    recolorir e obrigatorio. Este teste existe para impedir que alguem
    reverta a recoloracao achando que era enfeite.
    """
    paleta = theme.PALETA_CLARA if tema == "claro" else theme.PALETA_ESCURA
    obtido = razao(paleta[token], paleta["accent_soft"])
    assert obtido < 4.5, (
        f"[{tema}] {token} agora passa sobre a selecao com {obtido:.2f}:1. "
        "Se isso foi intencional, revise a necessidade de recolorir."
    )


def test_ink_serve_no_claro_e_reprova_no_escuro():
    """Por que `ink` nao pode ser a cor da selecao.

    Este e o par que enganou: no tema claro `ink` da 9.06:1 sobre a
    selecao e parece resolvido. No escuro o mesmo token vira claro e cai
    para 1.46:1, praticamente invisivel. Foi assim que o defeito passou
    despercebido ate aparecer na tela de alguem usando tema escuro.
    """
    assert razao(theme.PALETA_CLARA["ink"], theme.PALETA_CLARA["accent_soft"]) >= 4.5
    assert razao(theme.PALETA_ESCURA["ink"], theme.PALETA_ESCURA["accent_soft"]) < 2.0


def test_qss_pinta_selecao_com_on_accent():
    """A folha de estilo precisa mandar on_accent, e nao ink.

    Verificado no tema ESCURO de proposito: no claro os dois tokens tem o
    mesmo valor, entao o teste passaria sem provar nada.
    """
    import re

    try:
        theme.definir_tema("escuro")
        folha = theme.qss()
        bloco = re.search(r"QListWidget::item:selected:active\s*\{([^}]*)\}", folha)
        assert bloco, "nao ha regra para item selecionado ativo"
        corpo = bloco.group(1)
        assert theme.PALETA_ESCURA["on_accent"] in corpo, (
            "selecao ativa nao usa on_accent como cor de texto"
        )
        assert theme.PALETA_ESCURA["ink"] not in corpo, (
            "selecao ativa ainda usa ink, que some sobre o fundo claro da selecao"
        )
    finally:
        theme.definir_tema("claro")


@pytest.mark.parametrize("tema", ["claro", "escuro"])
def test_selecao_tem_o_mesmo_fundo_com_e_sem_foco(tema):
    """Os dois estados de selecao precisam usar o mesmo fundo.

    O QSS distingue `:selected` de `:selected:active`, e antes cada um
    usava um fundo diferente: `surface_alt` (escuro no tema escuro) e
    `accent_soft` (claro nos dois). O widget embutido nao tem como saber
    qual dos dois esta valendo, entao pintava o texto para um fundo e
    recebia o outro, e o resultado foi texto escuro sobre fundo escuro.

    Unificar custa a distincao visual entre janela focada e nao focada, e
    paga com legibilidade garantida. Foi uma troca deliberada.
    """
    import re

    try:
        theme.definir_tema(tema)
        folha = theme.qss()
        fundos = re.findall(
            r"QListWidget::item:selected(?::active)?\s*\{[^}]*?"
            r"background-color:\s*([^;]+);",
            folha,
        )
        assert len(fundos) >= 2, "faltam as duas regras de selecao"
        assert len(set(f.strip() for f in fundos)) == 1, (
            f"fundos de selecao diferentes: {fundos}"
        )
    finally:
        theme.definir_tema("claro")
