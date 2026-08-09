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


def test_escala_explicita_ignora_a_tela(qapp):
    """Quem gera arquivo precisa de pixels exatos, nao dos da tela.

    O .ico do executavel e desenhado com icons.pixmap. Se o tamanho
    dependesse do monitor, o mesmo `build.py` produziria bytes diferentes
    em cada maquina, e a arvore de trabalho ficaria suja depois de todo
    build.
    """
    p = icons.pixmap("arquivo", tamanho=32, escala=1.0)
    assert p.width() == 32 and p.height() == 32
    assert p.devicePixelRatio() == 1.0


def test_escala_explicita_de_verdade_multiplica(qapp):
    p = icons.pixmap("arquivo", tamanho=32, escala=2.0)
    assert p.width() == 64 and p.height() == 64


def test_escala_padrao_continua_seguindo_a_tela(qapp):
    """A adicao do parametro nao pode mudar o comportamento de quem nao usa."""
    from markitdown_gui.ui.icons import _escala

    p = icons.pixmap("arquivo", tamanho=32)
    assert p.width() == max(1, round(32 * _escala()))
