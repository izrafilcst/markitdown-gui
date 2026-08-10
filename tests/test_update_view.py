"""Testes do dialogo de atualizacao.

Nenhum teste aqui toca a internet: a camada de rede e substituida, do
mesmo jeito que em test_atualizacao.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from markitdown_gui import atualizacao
from markitdown_gui.ui.update_view import DialogoDeAtualizacao


def _esperar(qapp, condicao, segundos=10.0):
    """Espera a thread de rede responder, sem travar o event loop.

    Um laco de processEvents puro nao serve: ele gira mais rapido do que a
    thread consegue arrancar, e o teste conclui "nao respondeu" antes de a
    resposta existir. A pausa curta devolve tempo de CPU para a thread.
    """
    import time

    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        qapp.processEvents()
        if condicao():
            return True
        time.sleep(0.01)
    qapp.processEvents()
    return condicao()


@pytest.fixture
def sem_novidade(monkeypatch):
    monkeypatch.setattr(
        atualizacao, "verificar",
        lambda versao_instalada, tempo_limite=10: atualizacao.Resultado(
            disponivel=False, versao="1.0.0"
        ),
    )


@pytest.fixture
def com_novidade(monkeypatch):
    monkeypatch.setattr(
        atualizacao, "verificar",
        lambda versao_instalada, tempo_limite=10: atualizacao.Resultado(
            disponivel=True, versao="1.5.0",
            instalador="https://github.com/izrafilcst/markitdown-gui/"
                       "releases/download/v1.5.0/MarkItDown-Setup.exe",
            pagina="https://github.com/izrafilcst/markitdown-gui/releases",
            notas="Correcoes de acessibilidade.", tamanho=87_000_000,
        ),
    )


def test_abre_sem_consultar_nada(qapp, monkeypatch):
    """O dialogo nao pode telefonar para casa so por ter sido aberto."""
    chamadas = []
    monkeypatch.setattr(
        atualizacao, "verificar",
        lambda **k: chamadas.append(1) or atualizacao.Resultado(),
    )
    d = DialogoDeAtualizacao(versao="1.0.0")
    qapp.processEvents()
    assert chamadas == []
    assert "nao verifica" in d.texto_do_estado().lower()
    assert not d.oferece_atualizacao()


def test_mostra_a_versao_instalada(qapp):
    d = DialogoDeAtualizacao(versao="1.2.3")
    assert "1.2.3" in d.rotulo_instalada.text()


def test_ja_esta_atualizado(qapp, sem_novidade):
    d = DialogoDeAtualizacao(versao="1.0.0")
    d.verificar()
    assert _esperar(qapp, lambda: "recente" in d.texto_do_estado().lower())
    assert not d.oferece_atualizacao()


def test_oferece_quando_ha_versao_nova(qapp, com_novidade):
    d = DialogoDeAtualizacao(versao="1.0.0")
    d.verificar()
    assert _esperar(qapp, lambda: d.oferece_atualizacao())
    texto = d.texto_do_estado()
    assert "1.5.0" in texto
    assert "83 MB" in texto or "MB" in texto
    assert "historico" in texto.lower()


def test_erro_de_rede_aparece_sem_jargao(qapp, monkeypatch):
    monkeypatch.setattr(
        atualizacao, "verificar",
        lambda versao_instalada, tempo_limite=10: atualizacao.Resultado(
            erro="Nao foi possivel falar com o servidor. "
                 "Verifique sua conexao com a internet e tente de novo."
        ),
    )
    d = DialogoDeAtualizacao(versao="1.0.0")
    d.verificar()
    assert _esperar(qapp, lambda: "conexao" in d.texto_do_estado().lower())
    assert not d.oferece_atualizacao()
    for jargao in ("Traceback", "URLError", "Exception"):
        assert jargao not in d.texto_do_estado()


def test_download_falho_explica(qapp, com_novidade, monkeypatch):
    monkeypatch.setattr(
        atualizacao, "baixar_instalador",
        lambda url, pasta, tempo_limite=60, progresso=None: None,
    )
    d = DialogoDeAtualizacao(versao="1.0.0")
    d.verificar()
    assert _esperar(qapp, lambda: d.oferece_atualizacao())
    d.baixar_e_instalar()
    assert _esperar(qapp, lambda: "nao foi possivel baixar" in d.texto_do_estado().lower())


def test_download_bem_sucedido_guarda_o_caminho(qapp, com_novidade, monkeypatch, pasta):
    falso = pasta / "MarkItDown-Setup.exe"
    falso.write_bytes(b"instalador")
    monkeypatch.setattr(
        atualizacao, "baixar_instalador",
        lambda url, pasta_destino=None, tempo_limite=60, progresso=None: falso,
    )
    abertos = []
    monkeypatch.setattr(DialogoDeAtualizacao, "_abrir", lambda self, c: abertos.append(c))

    d = DialogoDeAtualizacao(versao="1.0.0")
    d.verificar()
    assert _esperar(qapp, lambda: d.oferece_atualizacao())
    d.baixar_e_instalar()
    assert _esperar(qapp, lambda: d.caminho_baixado() is not None)
    assert abertos == [falso]


def test_fechar_durante_a_consulta_nao_deixa_thread_solta(qapp, com_novidade):
    """Fechar no meio da consulta e caminho normal, nao excecao.

    Sem esperar a thread, o processo cai no encerramento. Aconteceu de
    verdade: a suite parava de imprimir o resumo final.
    """
    d = DialogoDeAtualizacao(versao="1.0.0")
    d.verificar()
    d.reject()
    qapp.processEvents()
    assert d._pool.activeThreadCount() == 0


def test_botoes_respeitam_o_alvo_minimo(qapp):
    from PySide6.QtWidgets import QPushButton

    d = DialogoDeAtualizacao(versao="1.0.0")
    for botao in d.findChildren(QPushButton):
        assert botao.minimumHeight() >= 32


def test_nao_usa_cor_literal():
    import re

    fonte = Path("markitdown_gui/ui/update_view.py").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{6}\b", fonte)
