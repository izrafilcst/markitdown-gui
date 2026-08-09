"""A barra de destino tambem aceita pasta solta.

Mesma armadilha do QMimeData do test_drop.py: o QDropEvent nao assume
posse do mime, entao o helper devolve os dois e quem chama segura os dois.
"""

from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QPushButton, QToolButton

from markitdown_gui.ui.destino_bar import BarraDestino


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


def test_pasta_solta_vira_destino(qapp, pasta):
    alvo = pasta / "saida"
    alvo.mkdir()

    barra = BarraDestino()
    spy = QSignalSpy(barra.destino_escolhido)
    evento, _mime = _evento_de_drop([alvo])
    barra.dropEvent(evento)

    assert spy.count() == 1
    recebido = spy.at(0)[0]
    assert recebido == alvo
    assert recebido.is_absolute()


def test_arquivo_solto_usa_a_pasta_dele(qapp, pasta):
    """Soltar arquivo na barra de destino e pedir a pasta que o contem.

    Recusar seria tecnicamente correto e praticamente inutil: a intencao
    de quem solta um arquivo ali e obvia.
    """
    arquivo = pasta / "documento.pdf"
    arquivo.write_text("x", encoding="utf-8")

    barra = BarraDestino()
    spy = QSignalSpy(barra.destino_escolhido)
    evento, _mime = _evento_de_drop([arquivo])
    barra.dropEvent(evento)

    assert spy.count() == 1
    assert spy.at(0)[0] == pasta


def test_drop_sem_url_nao_emite(qapp):
    mime = QMimeData()
    mime.setText("so texto")
    evento = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    barra = BarraDestino()
    spy = QSignalSpy(barra.destino_escolhido)
    barra.dropEvent(evento)
    assert spy.count() == 0


def test_definir_destino_mostra_o_caminho(qapp, pasta):
    barra = BarraDestino()
    barra.definir_destino(pasta)
    assert str(pasta) in barra.texto_do_destino()


def test_destino_none_explica_o_que_acontece(qapp):
    """Sem destino escolhido, o app grava ao lado do original."""
    barra = BarraDestino()
    barra.definir_destino(None)
    texto = barra.texto_do_destino().lower()
    assert "original" in texto or "mesma pasta" in texto


def test_definir_destino_nao_emite_sinal(qapp, pasta):
    """Setter e para refletir estado, nao para disparar acao.

    Se ele emitisse, o controller receberia de volta o destino que ele
    mesmo acabou de mandar, e isso vira laco infinito na janela principal.
    """
    barra = BarraDestino()
    spy = QSignalSpy(barra.destino_escolhido)
    barra.definir_destino(pasta)
    assert spy.count() == 0


def test_botao_abrir_pasta_emite(qapp, pasta):
    barra = BarraDestino()
    barra.definir_destino(pasta)
    spy = QSignalSpy(barra.abrir_pasta)
    barra.botao_abrir.click()
    assert spy.count() == 1


def _botoes(widget):
    """findChildren nao aceita tupla de tipos no PySide6, so um tipo por vez."""
    return widget.findChildren(QPushButton) + widget.findChildren(QToolButton)


def test_todo_botao_de_icone_tem_nome_acessivel(qapp):
    barra = BarraDestino()
    for botao in _botoes(barra):
        if not botao.text():
            assert botao.accessibleName(), "botao so de icone sem accessibleName"


def test_alvo_de_clique_minimo(qapp):
    barra = BarraDestino()
    for botao in _botoes(barra):
        assert botao.minimumHeight() >= 32
        assert botao.minimumWidth() >= 32
