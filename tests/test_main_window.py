from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from markitdown_gui.jobs.models import Estado, Item
from markitdown_gui.ui.main_window import MainWindow


def _evento_de_drop(caminhos: list[Path]) -> tuple[QDropEvent, QMimeData]:
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


def test_janela_abre_e_tem_os_blocos(qapp):
    janela = MainWindow()
    assert janela.windowTitle() == "MarkItDown"
    assert janela.drop_zone is not None
    assert janela.barra_destino is not None
    assert janela.lista is not None


def test_janela_inteira_aceita_drop(qapp):
    janela = MainWindow()
    assert janela.acceptDrops() is True


def test_fila_vazia_mostra_zona_grande(qapp):
    janela = MainWindow()
    assert janela.drop_zone.maximumHeight() > 100


def test_drop_na_janela_entra_na_fila(qapp, pasta):
    """A janela inteira e alvo de drop, nao so a zona."""
    arquivo = pasta / "documento.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    evento, _mime = _evento_de_drop([arquivo])
    janela.dropEvent(evento)
    qapp.processEvents()

    assert len(janela.controller.itens) == 1
    assert janela.lista.count() == 1


def test_fila_cheia_compacta_a_zona(qapp, pasta):
    arquivo = pasta / "documento.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    grande = janela.drop_zone.maximumHeight()
    janela.controller.adicionar([arquivo])
    qapp.processEvents()

    assert janela.drop_zone.maximumHeight() < grande


def test_recusado_aparece_na_barra_de_avisos(qapp, pasta):
    imagem = pasta / "foto.png"
    imagem.write_bytes(b"nao importa")

    janela = MainWindow()
    janela.controller.adicionar([imagem])
    qapp.processEvents()

    assert janela.barra_aviso.isVisibleTo(janela)
    assert janela.texto_do_aviso()


def test_destino_escolhido_chega_no_controller(qapp, pasta):
    janela = MainWindow()
    alvo = pasta / "saida"
    alvo.mkdir()
    janela.barra_destino.destino_escolhido.emit(alvo)
    qapp.processEvents()
    assert janela.controller.destino == alvo


def test_destino_do_controller_reflete_na_barra(qapp, pasta):
    janela = MainWindow()
    alvo = pasta / "saida"
    alvo.mkdir()
    janela.controller.definir_destino(alvo)
    qapp.processEvents()
    assert str(alvo) in janela.barra_destino.texto_do_destino()


def test_remover_pela_linha_tira_da_fila(qapp, pasta):
    arquivo = pasta / "documento.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    janela.controller.adicionar([arquivo])
    qapp.processEvents()
    alvo = janela.controller.itens[0].id

    janela.lista.remover_pedido.emit(alvo)
    qapp.processEvents()

    assert janela.controller.itens == []
    assert janela.lista.count() == 0


def test_estado_do_item_chega_na_linha(qapp, pasta):
    arquivo = pasta / "documento.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    janela.controller.adicionar([arquivo])
    qapp.processEvents()

    item = janela.controller.itens[0]
    item.estado = Estado.CONCLUIDO
    janela.controller.item_alterado.emit(item.id)
    qapp.processEvents()

    linha = janela.lista.linha(item.id)
    assert Estado.CONCLUIDO.rotulo in linha.texto_de_estado()


def test_fechar_encerra_o_controller(qapp):
    """Fechar durante conversao nao pode deixar processo orfao."""
    janela = MainWindow()
    chamadas = []
    janela.controller.encerrar = lambda: chamadas.append(1)
    janela.close()
    assert chamadas == [1]


def test_botao_converter_desabilitado_com_fila_vazia(qapp):
    janela = MainWindow()
    assert not janela.botao_converter.isEnabled()


def test_botao_converter_habilita_com_item(qapp, pasta):
    arquivo = pasta / "documento.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    janela.controller.adicionar([arquivo])
    qapp.processEvents()
    assert janela.botao_converter.isEnabled()


def test_detalhe_abre_dialogo_sem_travar(qapp, pasta):
    """O dialogo de detalhe tecnico existe e recebe o texto do item."""
    arquivo = pasta / "documento.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    janela.controller.adicionar([arquivo])
    qapp.processEvents()

    item = janela.controller.itens[0]
    item.estado = Estado.FALHOU
    item.mensagem = "Nao foi possivel ler o arquivo"
    item.detalhe = "FileConversionException: senha"

    assert janela.texto_de_detalhe(item.id) == item.detalhe


def test_conversao_ponta_a_ponta_pela_janela(qapp, pasta):
    """O caminho completo do usuario, sem atalho: soltar, escolher, converter."""
    origem = pasta / "entrada"
    origem.mkdir()
    for nome in ("um.csv", "dois.csv"):
        (origem / nome).write_text("a,b\n1,2\n", encoding="utf-8")
    destino = pasta / "saida"

    janela = MainWindow()
    evento, _mime = _evento_de_drop([origem])
    janela.dropEvent(evento)
    janela.barra_destino.destino_escolhido.emit(destino)
    qapp.processEvents()

    assert len(janela.controller.itens) == 2

    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    janela.controller.ocioso.connect(loop.quit)
    QTimer.singleShot(30000, loop.quit)
    janela.botao_converter.click()
    loop.exec()

    gerados = sorted(p.name for p in destino.glob("*.md"))
    assert gerados == ["dois_convertido.md", "um_convertido.md"]
    assert all(i.estado is Estado.CONCLUIDO for i in janela.controller.itens)
    janela.controller.encerrar()
