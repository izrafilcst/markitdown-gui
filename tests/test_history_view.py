"""Testes da aba de conversoes recentes."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QPushButton, QToolButton

from markitdown_gui.core.historico import Historico
from markitdown_gui.ui.history_view import AbaRecentes


@pytest.fixture
def livro(pasta):
    h = Historico(pasta / "historico.db")
    for nome in ("primeiro.pdf", "segundo.docx", "terceiro.csv"):
        h.registrar(
            origem=Path(r"C:\Downloads") / nome,
            destino=pasta / f"{Path(nome).stem}_convertido.md",
            caracteres=2500,
            sucesso=True,
        )
    return h


def _botoes(widget):
    return widget.findChildren(QPushButton) + widget.findChildren(QToolButton)


def test_lista_o_que_esta_no_historico(qapp, livro):
    aba = AbaRecentes(livro)
    assert aba.quantidade_exibida() == 3


def test_mais_recente_primeiro(qapp, livro):
    aba = AbaRecentes(livro)
    assert aba.nomes_exibidos()[0] == "terceiro.csv"


def test_mostra_a_data(qapp, livro):
    aba = AbaRecentes(livro)
    texto = aba.texto_da_linha(0)
    assert "hoje" in texto.lower() or "/" in texto


def test_mostra_o_tamanho_convertido(qapp, livro):
    aba = AbaRecentes(livro)
    assert "caracteres" in aba.texto_da_linha(0)


def test_historico_vazio_explica_em_vez_de_ficar_em_branco(qapp, pasta):
    """Tela vazia sem explicacao parece defeito."""
    aba = AbaRecentes(Historico(pasta / "vazio.db"))
    assert aba.quantidade_exibida() == 0
    assert aba.mensagem_de_vazio()
    assert aba.rotulo_vazio.isVisibleTo(aba)


def test_atualizar_traz_o_que_entrou_depois(qapp, livro, pasta):
    aba = AbaRecentes(livro)
    assert aba.quantidade_exibida() == 3

    livro.registrar(
        origem=Path(r"C:\Downloads\quarto.pdf"),
        destino=pasta / "quarto_convertido.md",
        caracteres=100,
        sucesso=True,
    )
    aba.atualizar()
    assert aba.quantidade_exibida() == 4
    assert aba.nomes_exibidos()[0] == "quarto.pdf"


def test_falha_aparece_com_o_motivo(qapp, pasta):
    h = Historico(pasta / "historico.db")
    h.registrar(
        origem=Path(r"C:\Downloads\ruim.pdf"),
        destino=Path(),
        caracteres=0,
        sucesso=False,
        mensagem="Arquivo corrompido",
    )
    aba = AbaRecentes(h)
    assert "corrompido" in aba.texto_da_linha(0).lower()


def test_limpar_apaga_e_esvazia_a_tela(qapp, livro):
    aba = AbaRecentes(livro)
    aba.limpar_tudo()
    assert aba.quantidade_exibida() == 0
    assert livro.recentes() == []


def test_abrir_pedido_emite_o_caminho(qapp, livro, pasta):
    alvo = pasta / "terceiro_convertido.md"
    alvo.write_text("conteudo", encoding="utf-8")

    aba = AbaRecentes(livro)
    spy = QSignalSpy(aba.abrir_pedido)
    aba.abrir_linha(0)
    assert spy.count() == 1
    assert spy.at(0)[0] == alvo


def test_nao_emite_abrir_para_arquivo_que_sumiu(qapp, pasta):
    """O convertido pode ter sido apagado desde entao."""
    h = Historico(pasta / "historico.db")
    h.registrar(
        origem=Path(r"C:\Downloads\a.pdf"),
        destino=pasta / "nunca_existiu.md",
        caracteres=10,
        sucesso=True,
    )
    aba = AbaRecentes(h)
    spy = QSignalSpy(aba.abrir_pedido)
    aba.abrir_linha(0)
    assert spy.count() == 0
    assert aba.mensagem_de_erro()


def test_todo_botao_de_icone_tem_nome_acessivel(qapp, livro):
    aba = AbaRecentes(livro)
    for botao in _botoes(aba):
        if not botao.text():
            assert botao.accessibleName(), "botao so de icone sem accessibleName"


def test_alvo_de_clique_minimo(qapp, livro):
    aba = AbaRecentes(livro)
    for botao in _botoes(aba):
        assert botao.minimumHeight() >= 32
        assert botao.minimumWidth() >= 32


def test_nao_usa_cor_literal(qapp, livro):
    """A aba precisa acompanhar o tema, entao le tudo de theme.COLOR."""
    import re

    fonte = Path("markitdown_gui/ui/history_view.py").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{6}\b", fonte)
