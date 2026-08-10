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


def test_drop_interno_anuncia_a_ordem(qapp):
    """O caminho real da reordenacao: dropEvent sem URL e movimento interno.

    O teste acima cobra o resultado da reordenacao chamando anunciar_ordem
    direto, o que nao exercita o dropEvent. Este cobra o gatilho: um drop
    que nao traz URL veio de dentro da propria lista, e a lista precisa
    anunciar a ordem resultante sozinha. Sem este teste, apagar a chamada
    de anunciar_ordem dentro do dropEvent passa despercebido.
    """
    lista = ListaDaFila()
    itens = _itens("a.pdf", "b.docx", "c.csv")
    lista.adicionar(itens)

    mime = QMimeData()
    mime.setData("application/x-qabstractitemmodeldatalist", b"")
    evento = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    spy = QSignalSpy(lista.ordem_alterada)
    lista.dropEvent(evento)

    assert spy.count() == 1
    assert spy.at(0)[0] == lista.ordem_atual()


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


NOME_LONGO = "Pearson VUE - It's time to test your system.pdf"


def test_linha_nao_e_cortada_dentro_da_lista(qapp):
    """A linha precisa caber inteira, com a folha de estilo aplicada.

    O QSS poe padding e margem em QListWidget::item, e esse espaco sai da
    area do widget embutido. Gravar no item o sizeHint cru da linha deixa
    o conteudo maior que o espaco disponivel, e o nome do arquivo aparece
    cortado ao meio. Foi exatamente o que apareceu na tela.
    """
    from markitdown_gui.ui import theme

    qapp.setStyleSheet(theme.qss())
    lista = ListaDaFila()
    lista.resize(900, 400)
    (item,) = [Item(origem=Path(NOME_LONGO), estado=Estado.CONCLUIDO)]
    lista.adicionar([item])
    lista.show()
    qapp.processEvents()

    linha = lista.linha(item.id)
    assert linha.height() >= linha.sizeHint().height(), (
        f"linha cortada: tem {linha.height()}px, precisa de "
        f"{linha.sizeHint().height()}px"
    )
    lista.close()
    qapp.setStyleSheet("")


def test_nome_longo_e_encurtado_e_nao_estoura(qapp):
    """Nome que nao cabe vira reticencias, e o completo fica no tooltip."""
    lista = ListaDaFila()
    lista.resize(320, 200)          # estreito de proposito
    item = Item(origem=Path("C:/Downloads") / NOME_LONGO)
    lista.adicionar([item])
    lista.show()
    qapp.processEvents()

    linha = lista.linha(item.id)
    exibido = linha.texto_do_nome()
    assert "\u2026" in exibido or len(exibido) < len(NOME_LONGO), (
        f"nome nao foi encurtado numa lista estreita: {exibido!r}"
    )
    assert NOME_LONGO in linha._nome.toolTip()
    lista.close()


def test_nome_curto_fica_intacto(qapp):
    lista = ListaDaFila()
    lista.resize(900, 200)
    item = Item(origem=Path("a.pdf"))
    lista.adicionar([item])
    lista.show()
    qapp.processEvents()
    assert lista.linha(item.id).texto_do_nome() == "a.pdf"
    lista.close()


def test_selecionar_linha_da_fila_recolore(qapp):
    """A fila tem o mesmo defeito de selecao que o historico tinha.

    Widget embutido nao herda `:selected` do QSS, entao sem recolorir o
    texto do estado fica com a cor de estado sobre o fundo claro da
    selecao. No tema escuro isso mede 1.06:1.
    """
    from markitdown_gui.ui import theme

    lista = ListaDaFila()
    (item,) = _itens("a.pdf")
    lista.adicionar([item])
    linha = lista.linha(item.id)

    assert linha.cor_do_texto() != theme.COLOR["on_accent"]
    lista.setCurrentRow(0)
    qapp.processEvents()
    assert linha.cor_do_texto() == theme.COLOR["on_accent"]

    lista.clearSelection()
    qapp.processEvents()
    assert linha.cor_do_texto() != theme.COLOR["on_accent"]


def test_selecao_da_fila_sobrevive_a_mudanca_de_estado(qapp):
    """Atualizar o item nao pode devolver a cor errada a uma linha selecionada."""
    from markitdown_gui.ui import theme

    lista = ListaDaFila()
    (item,) = _itens("a.pdf")
    lista.adicionar([item])
    lista.setCurrentRow(0)
    qapp.processEvents()

    item.estado = Estado.CONCLUIDO
    lista.atualizar(item)
    qapp.processEvents()

    assert lista.linha(item.id).cor_do_texto() == theme.COLOR["on_accent"]
