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
