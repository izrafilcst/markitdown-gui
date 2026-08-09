"""A premissa que justificou escolher Qt em vez de HTML mora aqui.

Um app web nao recebe o caminho absoluto de um arquivo solto, so o
conteudo. Este projeto precisa do caminho para converter em lote sem
copiar gigabytes para uma pasta temporaria. Se estes testes falharem, a
escolha de tecnologia do projeto estava errada.

Nota sobre QSignalSpy: nesta versao do PySide6 ele nao e mais sequencia,
entao `len(spy)` e `spy[0]` estouram TypeError. Os equivalentes que
funcionam sao `spy.count()` e `spy.at(0)`.
"""

from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtTest import QSignalSpy

from markitdown_gui.ui.drop_zone import DropZone


def _evento_de_drop(caminhos: list[Path]) -> tuple[QDropEvent, QMimeData]:
    """Monta um drop sintetico e devolve o QMimeData junto, de proposito.

    QDropEvent NAO assume posse do QMimeData. Se o mime for so uma variavel
    local de um helper que retorna apenas o evento, ele e coletado no
    retorno e o evento fica com ponteiro pendurado. O sintoma nao e um erro
    claro: `evento.mimeData()` passa a devolver um QObject generico, e
    qualquer `repr` no ponteiro morto derruba o processo inteiro com access
    violation no Windows.

    Devolver os dois obriga quem chama a segurar o mime pelo tempo da
    chamada, que e o que mantem o teste honesto.
    """
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


def test_drop_entrega_caminho_absoluto(qapp, pasta):
    """A premissa que justificou escolher Qt em vez de HTML."""
    arquivo = pasta / "teste.pdf"
    arquivo.write_text("x", encoding="utf-8")

    zona = DropZone()
    spy = QSignalSpy(zona.arquivos_soltos)
    evento, _mime = _evento_de_drop([arquivo])
    zona.dropEvent(evento)

    assert spy.count() == 1
    recebidos = spy.at(0)[0]
    assert recebidos[0].is_absolute()
    assert recebidos[0] == arquivo


def test_drop_de_multiplos(qapp, pasta):
    arquivos = []
    for nome in ("a.pdf", "b.docx"):
        alvo = pasta / nome
        alvo.write_text("x", encoding="utf-8")
        arquivos.append(alvo)

    zona = DropZone()
    spy = QSignalSpy(zona.arquivos_soltos)
    evento, _mime = _evento_de_drop(arquivos)
    zona.dropEvent(evento)
    assert len(spy.at(0)[0]) == 2


def test_drop_sem_url_nao_emite(qapp):
    """Soltar texto puro nao e soltar arquivo."""
    mime = QMimeData()
    mime.setText("so texto")
    evento = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    zona = DropZone()
    spy = QSignalSpy(zona.arquivos_soltos)
    zona.dropEvent(evento)
    assert spy.count() == 0


def test_compacto_muda_altura(qapp):
    zona = DropZone()
    alta = zona.maximumHeight()
    zona.definir_compacto(True)
    qapp.processEvents()
    assert zona.maximumHeight() < alta


def test_compacto_ida_e_volta(qapp):
    zona = DropZone()
    alta = zona.maximumHeight()
    zona.definir_compacto(True)
    qapp.processEvents()
    zona.definir_compacto(False)
    qapp.processEvents()
    assert zona.maximumHeight() == alta


def test_zona_aceita_drops(qapp):
    assert DropZone().acceptDrops() is True
