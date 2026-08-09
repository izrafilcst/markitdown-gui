"""Testes do historico de conversoes.

O historico e o unico dado que o app guarda alem da pasta de destino, e
ele guarda nome de arquivo, ou seja, informacao do usuario. Duas coisas
importam mais que o resto e por isso tem teste dedicado: ele nunca pode
derrubar uma conversao, e ele precisa poder ser apagado por completo.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from markitdown_gui.core import historico  # noqa: E402


@pytest.fixture
def livro(pasta):
    return historico.Historico(pasta / "historico.db")


def _registrar(livro, nome="a.pdf", **extra):
    dados = {
        "origem": Path(r"C:\Downloads") / nome,
        "destino": Path(r"C:\Saida") / f"{Path(nome).stem}_convertido.md",
        "caracteres": 1234,
        "sucesso": True,
        "mensagem": "",
    }
    dados.update(extra)
    return livro.registrar(**dados)


# ------------------------------------------------------------ gravacao

def test_registra_e_le_de_volta(livro):
    _registrar(livro, "relatorio.pdf")
    (r,) = livro.recentes()
    assert r.origem.name == "relatorio.pdf"
    assert r.destino.name == "relatorio_convertido.md"
    assert r.caracteres == 1234
    assert r.sucesso is True


def test_guarda_a_data_e_hora(livro):
    antes = datetime.now() - timedelta(seconds=2)
    _registrar(livro)
    (r,) = livro.recentes()
    assert isinstance(r.quando, datetime)
    assert r.quando >= antes
    assert r.quando <= datetime.now() + timedelta(seconds=2)


def test_falha_tambem_entra_com_o_motivo(livro):
    _registrar(livro, "ruim.pdf", sucesso=False, mensagem="Arquivo corrompido", caracteres=0)
    (r,) = livro.recentes()
    assert r.sucesso is False
    assert r.mensagem == "Arquivo corrompido"


def test_banco_e_criado_sozinho(pasta):
    alvo = pasta / "nova" / "funda" / "historico.db"
    livro = historico.Historico(alvo)
    _registrar(livro)
    assert alvo.exists()


# --------------------------------------------------------------- ordem

def test_mais_recente_vem_primeiro(livro):
    for nome in ("primeiro.pdf", "segundo.pdf", "terceiro.pdf"):
        _registrar(livro, nome)
    nomes = [r.origem.name for r in livro.recentes()]
    assert nomes == ["terceiro.pdf", "segundo.pdf", "primeiro.pdf"]


def test_limite_de_leitura(livro):
    for i in range(10):
        _registrar(livro, f"a{i}.pdf")
    assert len(livro.recentes(limite=3)) == 3


def test_historico_vazio_devolve_lista_vazia(livro):
    assert livro.recentes() == []


# ------------------------------------------------------------- limpeza

def test_limpar_apaga_tudo(livro):
    for i in range(5):
        _registrar(livro, f"a{i}.pdf")
    livro.limpar()
    assert livro.recentes() == []


def test_remover_um_so(livro):
    ids = [_registrar(livro, f"a{i}.pdf") for i in range(3)]
    livro.remover(ids[1])
    restantes = [r.id for r in livro.recentes()]
    assert ids[1] not in restantes
    assert len(restantes) == 2


def test_remover_id_inexistente_nao_estoura(livro):
    _registrar(livro)
    livro.remover(99999)
    assert len(livro.recentes()) == 1


def test_teto_de_registros(livro, monkeypatch):
    """O historico nao pode crescer para sempre no disco de ninguem."""
    monkeypatch.setattr(historico, "MAX_REGISTROS", 5)
    for i in range(12):
        _registrar(livro, f"a{i:02d}.pdf")
    guardados = livro.recentes(limite=100)
    assert len(guardados) == 5
    assert guardados[0].origem.name == "a11.pdf"


# ------------------------------------------------- nunca derrubar a fila

def test_erro_ao_gravar_nao_propaga(pasta, monkeypatch):
    """Historico quebrado nao pode impedir o usuario de converter.

    Guardar o registro e conveniencia; converter e o produto. Se o banco
    estiver corrompido, em disco cheio ou sem permissao, o app perde o
    historico daquele item e segue trabalhando.
    """
    livro = historico.Historico(pasta / "historico.db")
    _registrar(livro)

    import sqlite3

    def explodir(*args, **kwargs):
        raise sqlite3.OperationalError("disco cheio")

    monkeypatch.setattr(sqlite3, "connect", explodir)
    assert _registrar(livro, "outro.pdf") is None


def test_erro_ao_ler_devolve_vazio(pasta, monkeypatch):
    livro = historico.Historico(pasta / "historico.db")
    _registrar(livro)

    import sqlite3

    def explodir(*args, **kwargs):
        raise sqlite3.DatabaseError("banco corrompido")

    monkeypatch.setattr(sqlite3, "connect", explodir)
    assert livro.recentes() == []


def test_banco_corrompido_nao_derruba_a_leitura(pasta):
    alvo = pasta / "historico.db"
    alvo.write_bytes(b"isto nao e um banco sqlite" * 50)
    livro = historico.Historico(alvo)
    assert livro.recentes() == []


# -------------------------------------------------------------- formato

def test_data_formatada_para_humano(livro):
    _registrar(livro)
    (r,) = livro.recentes()
    texto = r.quando_legivel()
    assert len(texto) >= 10
    assert str(datetime.now().year) in texto or "hoje" in texto.lower()


def test_tamanho_legivel(livro):
    _registrar(livro, caracteres=0)
    (r,) = livro.recentes()
    assert r.tamanho_legivel()

    livro.limpar()
    _registrar(livro, caracteres=15000)
    (r,) = livro.recentes()
    assert "mil" in r.tamanho_legivel() or "15" in r.tamanho_legivel()


def test_caminho_padrao_fica_na_pasta_do_usuario(monkeypatch, pasta):
    monkeypatch.setenv("LOCALAPPDATA", str(pasta))
    caminho = historico.caminho_padrao()
    assert caminho.parent.name == "MarkItDown"
    assert caminho.name.endswith(".db")
