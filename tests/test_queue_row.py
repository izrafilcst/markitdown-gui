"""A linha da fila carrega a regra de acessibilidade mais dura do projeto.

Cor nunca pode ser o unico indicador de estado, por daltonismo. Todo
estado precisa de icone e texto tambem, e isso e verificado por maquina.

Nota: findChildren nao aceita tupla de tipos no PySide6, so um tipo por
chamada. O helper _botoes contorna isso.
"""

from pathlib import Path

import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QPushButton, QToolButton

from markitdown_gui.jobs.models import Estado, Item
from markitdown_gui.ui.queue_row import LinhaDaFila


def _botoes(widget):
    return widget.findChildren(QPushButton) + widget.findChildren(QToolButton)


@pytest.mark.parametrize("estado", list(Estado))
def test_toda_linha_mostra_icone_e_texto(qapp, estado):
    """Cor nunca pode ser o unico indicador de estado."""
    item = Item(origem=Path("a.pdf"), estado=estado)
    linha = LinhaDaFila(item)
    assert estado.rotulo in linha.texto_de_estado()


@pytest.mark.parametrize("estado", list(Estado))
def test_todo_estado_tem_icone(qapp, estado):
    item = Item(origem=Path("a.pdf"), estado=estado)
    linha = LinhaDaFila(item)
    assert not linha.icone_de_estado().isNull()


def test_botao_muda_conforme_estado(qapp):
    item = Item(origem=Path("a.pdf"))
    linha = LinhaDaFila(item)

    item.estado = Estado.PENDENTE
    linha.atualizar(item)
    assert linha.acao_visivel() == "remover"

    item.estado = Estado.FALHOU
    linha.atualizar(item)
    assert linha.acao_visivel() == "repetir"

    item.estado = Estado.CONCLUIDO
    linha.atualizar(item)
    assert linha.acao_visivel() == "abrir"

    item.estado = Estado.PROCESSANDO
    linha.atualizar(item)
    assert linha.acao_visivel() is None


def test_nome_do_arquivo_aparece(qapp):
    item = Item(origem=Path(r"C:\pasta\Relatorio 2024.docx"))
    linha = LinhaDaFila(item)
    assert "Relatorio 2024.docx" in linha.texto_do_nome()


def test_processando_mostra_barra_indeterminada(qapp):
    """O markitdown nao reporta progresso parcial.

    Fingir porcentagem seria mentira, entao a barra e indeterminada.
    """
    item = Item(origem=Path("a.pdf"), estado=Estado.PROCESSANDO)
    linha = LinhaDaFila(item)
    barra = linha.barra_de_progresso()
    assert barra.isVisibleTo(linha)
    assert barra.minimum() == 0 and barra.maximum() == 0


def test_pendente_nao_mostra_barra(qapp):
    item = Item(origem=Path("a.pdf"), estado=Estado.PENDENTE)
    linha = LinhaDaFila(item)
    assert not linha.barra_de_progresso().isVisibleTo(linha)


def test_mensagem_de_falha_aparece(qapp):
    item = Item(origem=Path("a.pdf"), estado=Estado.FALHOU)
    item.mensagem = "O arquivo foi movido ou apagado"
    linha = LinhaDaFila(item)
    linha.atualizar(item)
    assert "movido" in linha.texto_de_estado()


def test_remover_emite_com_o_id(qapp):
    item = Item(origem=Path("a.pdf"), estado=Estado.PENDENTE)
    linha = LinhaDaFila(item)
    spy = QSignalSpy(linha.remover_pedido)
    linha.botao_acao.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == item.id


def test_repetir_emite_com_o_id(qapp):
    item = Item(origem=Path("a.pdf"), estado=Estado.FALHOU)
    linha = LinhaDaFila(item)
    spy = QSignalSpy(linha.repetir_pedido)
    linha.botao_acao.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == item.id


def test_abrir_emite_com_o_id(qapp):
    item = Item(origem=Path("a.pdf"), estado=Estado.CONCLUIDO)
    linha = LinhaDaFila(item)
    spy = QSignalSpy(linha.abrir_pedido)
    linha.botao_acao.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == item.id


def test_detalhe_so_aparece_quando_ha_detalhe(qapp):
    item = Item(origem=Path("a.pdf"), estado=Estado.FALHOU)
    item.mensagem = "Nao foi possivel ler o arquivo"
    linha = LinhaDaFila(item)
    linha.atualizar(item)
    assert not linha.botao_detalhe.isVisibleTo(linha)

    item.detalhe = "FileConversionException: senha"
    linha.atualizar(item)
    assert linha.botao_detalhe.isVisibleTo(linha)

    spy = QSignalSpy(linha.detalhe_pedido)
    linha.botao_detalhe.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == item.id


def test_todo_botao_de_icone_tem_nome_acessivel(qapp):
    item = Item(origem=Path("a.pdf"))
    linha = LinhaDaFila(item)
    for botao in _botoes(linha):
        if not botao.text():
            assert botao.accessibleName(), "botao so de icone sem accessibleName"


def test_alvo_de_clique_minimo(qapp):
    item = Item(origem=Path("a.pdf"))
    linha = LinhaDaFila(item)
    for botao in _botoes(linha):
        assert botao.minimumHeight() >= 32
        assert botao.minimumWidth() >= 32


def test_atualizar_nao_troca_o_item(qapp):
    """A linha e reusada, nao recriada, quando o estado muda."""
    item = Item(origem=Path("a.pdf"))
    linha = LinhaDaFila(item)
    antes = linha.item_id
    item.estado = Estado.CONCLUIDO
    linha.atualizar(item)
    assert linha.item_id == antes
