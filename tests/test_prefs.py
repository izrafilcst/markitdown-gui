from pathlib import Path

from markitdown_gui.ui.prefs import Preferencias


def test_destino_ida_e_volta(qapp, pasta, monkeypatch):
    monkeypatch.setenv("QT_SCOPE_TESTE", "1")
    p = Preferencias()
    p.definir_destino(pasta)
    assert Preferencias().destino() == pasta


def test_destino_apagado_devolve_none(qapp, pasta):
    alvo = pasta / "some"
    alvo.mkdir()
    p = Preferencias()
    p.definir_destino(alvo)
    alvo.rmdir()
    assert Preferencias().destino() is None


def test_geometria_ida_e_volta(qapp):
    """Geometria e QByteArray opaco, so precisa voltar identico."""
    from PySide6.QtCore import QByteArray

    dados = QByteArray(b"geometria-de-teste")
    p = Preferencias()
    p.definir_geometria(dados)
    assert Preferencias().geometria() == dados


def test_geometria_nunca_gravada_devolve_none(qapp):
    p = Preferencias()
    p.limpar()
    assert p.geometria() is None


def test_destino_nunca_gravado_devolve_none(qapp):
    p = Preferencias()
    p.limpar()
    assert p.destino() is None


def test_destino_que_virou_arquivo_devolve_none(qapp, pasta):
    """Se o caminho existe mas nao e pasta, nao serve como destino."""
    alvo = pasta / "virou_arquivo"
    alvo.mkdir()
    p = Preferencias()
    p.definir_destino(alvo)
    alvo.rmdir()
    alvo.write_text("agora sou arquivo", encoding="utf-8")
    assert Preferencias().destino() is None
