"""Testes do verificador de atualizacoes.

A parte de rede e testada com um substituto, nunca chamando o GitHub de
verdade: teste que depende de internet falha por motivo errado, e falha
na maquina de quem esta sem conexao.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from markitdown_gui import atualizacao  # noqa: E402


# ------------------------------------------------- comparacao de versao

@pytest.mark.parametrize(
    "instalada,publicada,ha_novidade",
    [
        ("1.0.0", "1.0.1", True),
        ("1.0.0", "1.1.0", True),
        ("1.0.0", "2.0.0", True),
        ("1.0.0", "1.0.0", False),
        ("1.0.1", "1.0.0", False),
        ("2.0.0", "1.9.9", False),
        ("1.9.0", "1.10.0", True),      # 10 e maior que 9, e nao "1" < "9"
        ("1.0", "1.0.1", True),
        ("1.0.0", "v1.0.1", True),      # o "v" da tag nao pode atrapalhar
        ("v1.0.0", "1.0.0", False),
    ],
)
def test_compara_versao(instalada, publicada, ha_novidade):
    assert atualizacao.ha_versao_nova(instalada, publicada) is ha_novidade


def test_versao_ilegivel_nao_estoura():
    """Tag estranha no GitHub nao pode derrubar o app."""
    assert atualizacao.ha_versao_nova("1.0.0", "nightly-build") is False
    assert atualizacao.ha_versao_nova("nao-e-versao", "1.0.0") is False
    assert atualizacao.ha_versao_nova("1.0.0", "") is False


# ------------------------------------------------------ leitura da API

_RESPOSTA = {
    "tag_name": "v1.2.0",
    "html_url": "https://github.com/izrafilcst/markitdown-gui/releases/tag/v1.2.0",
    "body": "Correcoes de acessibilidade.",
    "assets": [
        {"name": "MarkItDown-Setup.exe",
         "browser_download_url": "https://exemplo/MarkItDown-Setup.exe",
         "size": 87000000},
        {"name": "outro.txt", "browser_download_url": "https://exemplo/o.txt",
         "size": 10},
    ],
}


@pytest.fixture
def rede_falsa(monkeypatch):
    def responder(url, tempo_limite=10):
        responder.pedidos.append(url)
        return json.dumps(_RESPOSTA).encode("utf-8")

    responder.pedidos = []
    monkeypatch.setattr(atualizacao, "_buscar", responder)
    return responder


def test_encontra_a_versao_publicada(rede_falsa):
    r = atualizacao.verificar(versao_instalada="1.0.0")
    assert r.disponivel is True
    assert r.versao == "1.2.0"
    assert r.instalador.endswith("MarkItDown-Setup.exe")
    assert r.pagina.startswith("https://github.com/")
    assert r.erro == ""


def test_sem_novidade_quando_ja_esta_atualizado(rede_falsa):
    r = atualizacao.verificar(versao_instalada="1.2.0")
    assert r.disponivel is False
    assert r.versao == "1.2.0"


def test_versao_mais_nova_que_a_publicada(rede_falsa):
    r = atualizacao.verificar(versao_instalada="9.9.9")
    assert r.disponivel is False


def test_consulta_so_o_repositorio_do_projeto(rede_falsa):
    atualizacao.verificar(versao_instalada="1.0.0")
    (url,) = rede_falsa.pedidos
    assert url == atualizacao.URL_DA_ULTIMA_VERSAO
    assert "markitdown-gui" in url


def test_sem_internet_devolve_erro_legivel(monkeypatch):
    def cair(url, tempo_limite=10):
        raise OSError("getaddrinfo failed")

    monkeypatch.setattr(atualizacao, "_buscar", cair)
    r = atualizacao.verificar(versao_instalada="1.0.0")
    assert r.disponivel is False
    assert r.erro
    assert "internet" in r.erro.lower() or "conex" in r.erro.lower()
    for jargao in ("Traceback", "getaddrinfo", "Exception"):
        assert jargao not in r.erro


def test_resposta_corrompida_nao_estoura(monkeypatch):
    monkeypatch.setattr(atualizacao, "_buscar", lambda u, tempo_limite=10: b"nao e json")
    r = atualizacao.verificar(versao_instalada="1.0.0")
    assert r.disponivel is False
    assert r.erro


def test_release_sem_instalador(monkeypatch):
    sem_exe = dict(_RESPOSTA, assets=[{"name": "leiame.txt",
                                       "browser_download_url": "https://x/l.txt",
                                       "size": 5}])
    monkeypatch.setattr(
        atualizacao, "_buscar", lambda u, tempo_limite=10: json.dumps(sem_exe).encode()
    )
    r = atualizacao.verificar(versao_instalada="1.0.0")
    assert r.disponivel is False
    assert "instalador" in r.erro.lower()


# ------------------------------------------------------------- download

def test_baixa_para_a_pasta_temporaria(monkeypatch, pasta):
    monkeypatch.setattr(
        atualizacao, "_buscar", lambda u, tempo_limite=60: b"conteudo do instalador"
    )
    destino = atualizacao.baixar_instalador(
        "https://github.com/izrafilcst/markitdown-gui/releases/download/"
        "v1.2.0/MarkItDown-Setup.exe",
        pasta,
    )
    assert destino.exists()
    assert destino.name == "MarkItDown-Setup.exe"
    assert destino.read_bytes() == b"conteudo do instalador"


def test_download_que_falha_devolve_none(monkeypatch, pasta):
    def cair(url, tempo_limite=60):
        raise OSError("conexao caiu")

    monkeypatch.setattr(atualizacao, "_buscar", cair)
    url = "https://github.com/izrafilcst/markitdown-gui/releases/download/v1/x.exe"
    assert atualizacao.baixar_instalador(url, pasta) is None


def test_download_recusa_url_de_fora_do_github(pasta):
    """Nao baixar executavel de qualquer lugar.

    A URL vem de uma resposta de rede. Se alguem conseguir devolver outra
    coisa, baixar e executar um .exe arbitrario seria o pior desfecho
    possivel. A origem e conferida antes de gravar qualquer byte.
    """
    assert atualizacao.baixar_instalador("https://malicioso.exemplo/x.exe", pasta) is None
    assert atualizacao.baixar_instalador("http://github.com/x.exe", pasta) is None


def test_url_do_github_e_aceita():
    assert atualizacao.origem_confiavel(
        "https://github.com/izrafilcst/markitdown-gui/releases/download/v1/x.exe"
    )
    assert atualizacao.origem_confiavel(
        "https://objects.githubusercontent.com/algum-caminho"
    )
    assert not atualizacao.origem_confiavel("https://github.com.malicioso.io/x.exe")
    assert not atualizacao.origem_confiavel("ftp://github.com/x.exe")
