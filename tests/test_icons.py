import pytest

from markitdown_gui.ui import icons

NOMES = [
    "arquivo", "pasta", "pasta-aberta", "upload", "check", "alerta", "x",
    "repetir", "abrir-externo", "pausar", "tocar", "lixeira", "arrastar",
    "ampulheta", "info",
]


@pytest.mark.parametrize("nome", NOMES)
def test_todo_icone_do_contrato_existe(qapp, nome):
    icone = icons.icone(nome)
    assert not icone.isNull(), f"icone '{nome}' nao renderizou"


def test_icone_desconhecido_falha_alto(qapp):
    """Nome errado deve estourar, nao devolver quadrado vazio silencioso."""
    with pytest.raises(KeyError):
        icons.icone("nome-que-nao-existe")


def test_recoloracao(qapp):
    from markitdown_gui.ui import theme
    a = icons.pixmap("check", theme.COLOR["ink"]).toImage()
    b = icons.pixmap("check", theme.COLOR["danger_text"]).toImage()
    assert a != b, "recolorir nao teve efeito"
