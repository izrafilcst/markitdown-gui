from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtTest import QSignalSpy

from markitdown_gui.jobs.models import Estado, Item
from markitdown_gui.ui.queue_row import LinhaDaFila
from markitdown_gui.ui.queue_view import ListaDaFila


def _itens(*nomes: str) -> list[Item]:
    return [Item(origem=Path(n)) for n in nomes]


def _evento_de_drop(caminhos: list[Path]) -> tuple[QDropEvent, QMimeData]:
    """Devolve o mime junto: o QDropEvent nao assume posse dele."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in caminhos])
    evento = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    return evento, mime


def test_adicionar_cria_uma_linha_por_item(qapp):
    lista = ListaDaFila()
    lista.adicionar(_itens("a.pdf", "b.docx", "c.csv"))
    assert lista.count() == 3


def test_adicionar_duas_vezes_acumula(qapp):
    lista = ListaDaFila()
    lista.adicionar(_itens("a.pdf"))
    lista.adicionar(_itens("b.docx"))
    assert lista.count() == 2


def test_atualizar_nao_recria_a_linha(qapp):
    """Recriar perderia foco de teclado e posicao de rolagem no meio do lote."""
    lista = ListaDaFila()
    (item,) = _itens("a.pdf")
    lista.adicionar([item])
    linha_antes = lista.linha(item.id)

    item.estado = Estado.CONCLUIDO
    lista.atualizar(item)

    assert lista.linha(item.id) is linha_antes
    assert lista.count() == 1
    assert Estado.CONCLUIDO.rotulo in linha_antes.texto_de_estado()


def test_atualizar_item_desconhecido_nao_estoura(qapp):
    lista = ListaDaFila()
    (fantasma,) = _itens("nunca_adicionado.pdf")
    lista.atualizar(fantasma)
    assert lista.count() == 0


def test_remover_tira_so_o_alvo(qapp):
    lista = ListaDaFila()
    itens = _itens("a.pdf", "b.docx", "c.csv")
    lista.adicionar(itens)
    lista.remover([itens[1].id])
    assert lista.count() == 2
    assert lista.ordem_atual() == [itens[0].id, itens[2].id]


def test_remover_id_inexistente_nao_estoura(qapp):
    lista = ListaDaFila()
    lista.adicionar(_itens("a.pdf"))
    lista.remover(["item-que-nao-existe"])
    assert lista.count() == 1


def test_limpar_tudo(qapp):
    lista = ListaDaFila()
    lista.adicionar(_itens("a.pdf", "b.docx"))
    lista.limpar_tudo()
    assert lista.count() == 0
    assert lista.ordem_atual() == []


def test_reordenar_emite_ordem_nova(qapp):
    lista = ListaDaFila()
    itens = _itens("a.pdf", "b.docx", "c.csv")
    lista.adicionar(itens)

    spy = QSignalSpy(lista.ordem_alterada)
    # Simula o fim de um arraste interno: o QListWidget ja reposicionou as
    # linhas, e o widget so precisa anunciar a ordem resultante.
    lista.mover_para_teste(0, 2)
    lista.anunciar_ordem()

    assert spy.count() == 1
    assert spy.at(0)[0] == [itens[1].id, itens[2].id, itens[0].id]
    assert lista.ordem_atual() == [itens[1].id, itens[2].id, itens[0].id]


def test_arquivo_solto_na_lista_emite(qapp, pasta):
    arquivo = pasta / "solto.pdf"
    arquivo.write_text("x", encoding="utf-8")

    lista = ListaDaFila()
    lista.adicionar(_itens("a.pdf"))
    spy = QSignalSpy(lista.arquivos_soltos)
    evento, _mime = _evento_de_drop([arquivo])
    lista.dropEvent(evento)

    assert spy.count() == 1
    assert spy.at(0)[0][0] == arquivo


def test_drop_externo_nao_altera_a_ordem(qapp, pasta):
    """Soltar arquivo de fora e adicionar, nao reordenar."""
    arquivo = pasta / "solto.pdf"
    arquivo.write_text("x", encoding="utf-8")

    lista = ListaDaFila()
    itens = _itens("a.pdf", "b.docx")
    lista.adicionar(itens)
    spy = QSignalSpy(lista.ordem_alterada)
    evento, _mime = _evento_de_drop([arquivo])
    lista.dropEvent(evento)

    assert spy.count() == 0
    assert lista.ordem_atual() == [i.id for i in itens]


def test_sinais_da_linha_chegam_na_lista(qapp):
    lista = ListaDaFila()
    itens = _itens("a.pdf")
    lista.adicionar(itens)
    linha: LinhaDaFila = lista.linha(itens[0].id)

    spy = QSignalSpy(lista.remover_pedido)
    linha.botao_acao.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == itens[0].id


def test_repetir_e_abrir_tambem_sobem(qapp):
    lista = ListaDaFila()
    (item,) = _itens("a.pdf")
    lista.adicionar([item])
    linha = lista.linha(item.id)

    item.estado = Estado.FALHOU
    lista.atualizar(item)
    spy_repetir = QSignalSpy(lista.repetir_pedido)
    linha.botao_acao.click()
    assert spy_repetir.count() == 1

    item.estado = Estado.CONCLUIDO
    lista.atualizar(item)
    spy_abrir = QSignalSpy(lista.abrir_pedido)
    linha.botao_acao.click()
    assert spy_abrir.count() == 1


def test_lista_aceita_drops(qapp):
    assert ListaDaFila().acceptDrops() is True
