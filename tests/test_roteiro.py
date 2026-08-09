"""O roteiro de verificacao manual do Task 14, na parte que da para automatizar.

Isto NAO substitui a verificacao manual. O que um teste nao alcanca esta
listado no fim deste arquivo e continua sendo trabalho humano, porque o
arraste vindo do Explorer atravessa o sistema operacional e nenhum evento
sintetico prova que ele funciona.

O que da para automatizar, e o que este arquivo faz, e tudo o que acontece
depois que os caminhos chegam ao app: fila, conversao, falha, repeticao,
pausa, reordenacao, navegacao por teclado, fechamento limpo e memoria da
pasta de destino. Isso e a maior parte do roteiro.

Os arquivos usados sao binarios de verdade, PDF e DOCX incluidos, gerados
por tests/fixtures/gerar_formatos.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, Qt, QThreadPool, QTimer
from PySide6.QtWidgets import QPushButton, QToolButton

sys.path.insert(0, str(Path(__file__).parent))

from fixtures.gerar_formatos import gerar_todos  # noqa: E402

from markitdown_gui.jobs.models import Estado  # noqa: E402
from markitdown_gui.ui import theme  # noqa: E402
from markitdown_gui.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture
def formatos(pasta):
    """Arquivos binarios reais: pdf, docx, pdf sem texto, pdf ruim, png."""
    return gerar_todos(pasta / "formatos")


class EsperaOcioso:
    """Espera a fila esvaziar soltando o GIL, como o app real faz.

    Duas armadilhas moram aqui, e as duas ja custaram tempo neste projeto.

    A primeira: `QSignalSpy.wait` roda o event loop segurando o GIL, e os
    workers, que sao codigo Python, nunca chegam a rodar. `QEventLoop.exec`
    solta o GIL, igual `QApplication.exec` no app de verdade.

    A segunda: conectar ao sinal DEPOIS de mandar converter e uma corrida.
    Um lote pequeno termina antes da conexao existir, o sinal se perde e a
    espera vai ate o timeout. Por isso a conexao acontece na construcao,
    antes de qualquer acao, e `esperar` ainda checa se a fila ja parou.
    """

    def __init__(self, janela: MainWindow) -> None:
        self._janela = janela
        self.recebido = False
        self._loop = QEventLoop()
        janela.controller.ocioso.connect(self._ao_ocioso)

    def _ao_ocioso(self) -> None:
        self.recebido = True
        self._loop.quit()

    def esperar(self, ms: int = 60000) -> bool:
        if self.recebido or not self._janela.controller.ativo:
            return True
        QTimer.singleShot(ms, self._loop.quit)
        self._loop.exec()
        return self.recebido or not self._janela.controller.ativo


# ---------------------------------------------------------------- item 1

def test_tres_formatos_diferentes_entram_na_fila(qapp, formatos):
    janela = MainWindow()
    janela.controller.adicionar(
        [formatos["pdf"], formatos["docx"], formatos["pdf_vazio"]]
    )
    qapp.processEvents()

    assert len(janela.controller.itens) == 3
    assert janela.lista.count() == 3
    extensoes = sorted(i.origem.suffix for i in janela.controller.itens)
    assert extensoes == [".docx", ".pdf", ".pdf"]


# ---------------------------------------------------------------- item 2

def test_pasta_com_subpastas_entra_inteira(qapp, pasta):
    raiz = pasta / "arvore"
    (raiz / "nivel1" / "nivel2").mkdir(parents=True)
    (raiz / "topo.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (raiz / "nivel1" / "meio.json").write_text('{"x": 1}', encoding="utf-8")
    (raiz / "nivel1" / "nivel2" / "fundo.html").write_text(
        "<html><body><p>fundo</p></body></html>", encoding="utf-8"
    )
    (raiz / "nivel1" / "ignorar.dll").write_bytes(b"lixo")

    janela = MainWindow()
    janela.controller.adicionar([raiz])
    qapp.processEvents()

    nomes = sorted(i.origem.name for i in janela.controller.itens)
    assert nomes == ["fundo.html", "meio.json", "topo.csv"]


# ---------------------------------------------------------------- item 3

def test_png_recusado_com_motivo_visivel(qapp, formatos):
    janela = MainWindow()
    janela.controller.adicionar([formatos["png"]])
    qapp.processEvents()

    assert janela.controller.itens == []
    assert janela.barra_aviso.isVisibleTo(janela)
    aviso = janela.texto_do_aviso().lower()
    assert aviso, "recusa silenciosa e o pior resultado possivel"
    assert "online" in aviso or "imagem" in aviso


# ---------------------------------------------------------------- item 4

def test_converter_gera_md_no_destino(qapp, formatos, pasta):
    destino = pasta / "saida"
    janela = MainWindow()
    janela.barra_destino.destino_escolhido.emit(destino)
    janela.controller.adicionar([formatos["pdf"], formatos["docx"]])
    qapp.processEvents()

    espera = EsperaOcioso(janela)
    janela.botao_converter.click()
    assert espera.esperar(), "a fila nao terminou"

    gerados = sorted(p.name for p in destino.glob("*.md"))
    assert gerados == ["contrato_convertido.md", "relatorio_convertido.md"]

    conteudo = (destino / "relatorio_convertido.md").read_text(encoding="utf-8")
    assert "cavalos" in conteudo, "o PDF converteu mas perdeu o texto"

    acento = (destino / "contrato_convertido.md").read_text(encoding="utf-8")
    assert "coracao" in acento
    janela.controller.encerrar()


# ---------------------------------------------------------------- item 5

def test_falha_mostra_mensagem_sem_jargao(qapp, formatos, pasta):
    janela = MainWindow()
    janela.barra_destino.destino_escolhido.emit(pasta / "saida")
    janela.controller.adicionar([formatos["pdf_ruim"]])
    qapp.processEvents()

    espera = EsperaOcioso(janela)
    janela.botao_converter.click()
    assert espera.esperar()

    item = janela.controller.itens[0]
    assert item.estado is Estado.FALHOU
    assert item.mensagem
    for jargao in ("Exception", "Error", "Traceback", "None", "raise"):
        assert jargao not in item.mensagem, (
            f"a mensagem que vai para a tela contem jargao: {item.mensagem!r}"
        )
    # O detalhe tecnico pode e deve conter jargao: ele fica escondido.
    assert item.detalhe
    janela.controller.encerrar()


def test_pdf_digitalizado_avisa_em_vez_de_calar(qapp, formatos, pasta):
    destino = pasta / "saida"
    janela = MainWindow()
    janela.barra_destino.destino_escolhido.emit(destino)
    janela.controller.adicionar([formatos["pdf_vazio"]])
    qapp.processEvents()

    espera = EsperaOcioso(janela)
    janela.botao_converter.click()
    assert espera.esperar()

    item = janela.controller.itens[0]
    assert item.estado is Estado.CONCLUIDO
    assert item.caracteres == 0
    assert "texto" in item.mensagem.lower()
    linha = janela.lista.linha(item.id)
    assert item.mensagem in linha.texto_de_estado()
    janela.controller.encerrar()


# ---------------------------------------------------------------- item 6

def test_repetir_o_item_que_falhou(qapp, formatos, pasta):
    janela = MainWindow()
    janela.barra_destino.destino_escolhido.emit(pasta / "saida")
    janela.controller.adicionar([formatos["pdf_ruim"]])
    qapp.processEvents()

    espera = EsperaOcioso(janela)
    janela.botao_converter.click()
    assert espera.esperar()
    item = janela.controller.itens[0]
    assert item.estado is Estado.FALHOU

    linha = janela.lista.linha(item.id)
    assert linha.acao_visivel() == "repetir"
    linha.botao_acao.click()
    qapp.processEvents()

    assert item.estado is Estado.PENDENTE
    assert item.mensagem == ""
    janela.controller.encerrar()


# ---------------------------------------------------------------- item 7

def test_pausar_no_meio_de_um_lote(qapp, pasta):
    origem = pasta / "lote"
    origem.mkdir()
    for i in range(20):
        (origem / f"arquivo_{i:02d}.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    janela.barra_destino.destino_escolhido.emit(pasta / "saida")
    janela.controller.adicionar([origem])
    qapp.processEvents()
    assert len(janela.controller.itens) == 20

    janela.controller.pausar()
    janela.controller.iniciar()
    qapp.processEvents()

    assert janela.controller.pausado
    assert all(i.estado is Estado.PENDENTE for i in janela.controller.itens)

    espera = EsperaOcioso(janela)
    janela.controller.retomar()
    assert espera.esperar()
    assert all(i.estado is Estado.CONCLUIDO for i in janela.controller.itens)
    janela.controller.encerrar()


# ---------------------------------------------------------------- item 8

def test_reordenar_muda_a_ordem_no_controller(qapp, pasta):
    origem = pasta / "tres"
    origem.mkdir()
    for nome in ("a.csv", "b.csv", "c.csv"):
        (origem / nome).write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    janela.controller.adicionar([origem])
    qapp.processEvents()

    invertida = [i.id for i in reversed(janela.controller.itens)]
    janela.lista.ordem_alterada.emit(invertida)
    qapp.processEvents()

    assert [i.id for i in janela.controller.itens] == invertida


# ---------------------------------------------------------------- item 9

def test_tab_alcanca_todos_os_controles(qapp, formatos):
    """Navegacao so por teclado precisa chegar em tudo que e clicavel."""
    janela = MainWindow()
    janela.controller.adicionar([formatos["pdf"]])
    janela.show()
    qapp.processEvents()

    clicaveis = [
        w
        for w in janela.findChildren(QPushButton) + janela.findChildren(QToolButton)
        if w.isVisibleTo(janela) and w.isEnabled()
    ]
    assert clicaveis, "a janela nao tem nenhum botao visivel"

    janela.drop_zone.setFocus()
    visitados = set()
    for _ in range(120):
        atual = qapp.focusWidget()
        if atual is None:
            break
        visitados.add(atual)
        if not janela.focusNextChild():
            break

    nao_alcancados = [
        w.accessibleName() or w.text() or w.objectName()
        for w in clicaveis
        if w not in visitados
    ]
    assert not nao_alcancados, f"inalcancavel por Tab: {nao_alcancados}"
    janela.close()


def test_existe_indicador_de_foco_visivel(qapp):
    """Foco precisa ser visto, nao so existir."""
    folha = theme.qss()
    assert ":focus" in folha, "a folha de estilo nao define nenhum estado de foco"
    assert theme.COLOR["focus"] in folha, "o token de foco nao e usado no QSS"


@pytest.mark.parametrize(
    "tecla", [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space]
)
def test_zona_de_arraste_responde_ao_teclado(qapp, tecla):
    """Quem navega por Tab precisa conseguir acionar a zona sem mouse.

    A zona e testada solta, e nao pela janela, de proposito: dentro da
    MainWindow o sinal `clicada` abre o QFileDialog, que e modal e trava o
    teste para sempre no modo offscreen. Que ele abra o dialogo e o
    comportamento certo do app; o que nao pode e este teste depender disso.
    """
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtTest import QSignalSpy

    from markitdown_gui.ui.drop_zone import DropZone

    zona = DropZone()
    spy = QSignalSpy(zona.clicada)
    zona.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, tecla, Qt.KeyboardModifier.NoModifier)
    )
    assert spy.count() == 1


# --------------------------------------------------------------- item 10

def test_fechar_durante_conversao_nao_deixa_worker_solto(qapp, pasta):
    origem = pasta / "lote"
    origem.mkdir()
    for i in range(12):
        (origem / f"a{i:02d}.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    janela = MainWindow()
    janela.barra_destino.destino_escolhido.emit(pasta / "saida")
    janela.controller.adicionar([origem])
    qapp.processEvents()

    janela.botao_converter.click()
    qapp.processEvents()
    janela.close()          # fecha no meio, e o closeEvent chama encerrar
    qapp.processEvents()

    assert QThreadPool.globalInstance().activeThreadCount() == 0, (
        "sobrou worker rodando depois de fechar a janela"
    )


# --------------------------------------------------------------- item 11

def test_destino_e_lembrado_entre_sessoes(qapp, pasta):
    """Fecha e reabre: a pasta escolhida precisa voltar sozinha."""
    destino = pasta / "destino_lembrado"
    destino.mkdir()

    primeira = MainWindow()
    primeira.barra_destino.destino_escolhido.emit(destino)
    qapp.processEvents()
    assert primeira.controller.destino == destino
    primeira.close()

    segunda = MainWindow()
    qapp.processEvents()
    assert segunda.controller.destino == destino
    assert str(destino) in segunda.barra_destino.texto_do_destino()
    segunda.close()


# ------------------------------------------------------------------------
# O que continua sendo trabalho humano, e por que:
#
#   - Arrastar do Explorer de verdade. Os testes injetam QDropEvent, que
#     prova o tratamento do evento, nao a travessia do sistema operacional.
#   - Conversao acionada pela janela do .exe empacotado. O que foi provado
#     e que a pilha converte congelada, com um executavel de console.
#   - Foco visivel de fato: o teste confirma que o QSS define o estado de
#     foco e usa o token certo, mas ninguem olhou para a tela.
#   - Leitor de tela (Narrator, NVDA) e modo de alto contraste do Windows.
#   - Ausencia de python.exe orfao no Gerenciador de Tarefas. O teste
#     verifica o pool de threads do processo, que e o mecanismo real, mas
#     nao inspeciona a lista de processos do sistema.
