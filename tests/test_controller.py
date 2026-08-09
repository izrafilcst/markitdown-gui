from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
from PySide6.QtTest import QSignalSpy

from markitdown_gui.jobs.controller import FilaController
from markitdown_gui.jobs.models import Estado


class EsperaOcioso:
    """Espera o sinal `ocioso` sem travar os workers.

    Aqui nao da para usar `QSignalSpy.wait`: ele roda o event loop segurando
    o GIL, e como os workers de conversao sao codigo Python, eles ficam
    parados esperando o GIL soltar. Resultado: nenhum arquivo e gravado e o
    sinal nunca chega, mesmo com trinta segundos de espera.

    `QEventLoop.exec` solta o GIL, que e exatamente o que
    `QApplication.exec` faz no app de verdade. Ou seja, este substituto e
    mais fiel ao que acontece em producao do que o QSignalSpy seria.
    """

    def __init__(self, controller: FilaController) -> None:
        self.recebido = False
        self._loop = QEventLoop()
        controller.ocioso.connect(self._ao_ocioso)

    def _ao_ocioso(self) -> None:
        self.recebido = True
        self._loop.quit()

    def esperar(self, timeout_ms: int = 30000) -> bool:
        if not self.recebido:
            QTimer.singleShot(timeout_ms, self._loop.quit)
            self._loop.exec()
        return self.recebido


@pytest.fixture
def app():
    # Precisa ser QApplication e nao QCoreApplication: os testes de widget da
    # mesma suite criam QApplication, e as duas classes nao coexistem no mesmo
    # processo. Quem chegar primeiro define o tipo para todos.
    inst = QCoreApplication.instance()
    if inst is None:
        from PySide6.QtWidgets import QApplication

        inst = QApplication([])
    return inst


@pytest.fixture
def entradas(pasta):
    origem = pasta / "entrada"
    origem.mkdir()
    for nome in ("a.csv", "b.csv", "c.csv"):
        (origem / nome).write_text("x,y\n1,2\n", encoding="utf-8")
    return origem


def test_adicionar_emite_e_popula(app, entradas):
    c = FilaController()
    spy = QSignalSpy(c.itens_adicionados)
    c.adicionar([entradas])
    assert len(c.itens) == 3
    # `count`, e nao `len`: QSignalSpy do PySide6 6.11 nao e mais sequencia.
    assert spy.count() == 1


def test_adicionar_duas_vezes_nao_duplica(app, entradas):
    c = FilaController()
    c.adicionar([entradas])
    c.adicionar([entradas])
    assert len(c.itens) == 3


def test_remover_tira_da_fila(app, entradas):
    c = FilaController()
    c.adicionar([entradas])
    alvo = c.itens[0].id
    c.remover([alvo])
    assert alvo not in [i.id for i in c.itens]


def test_remover_ignora_item_em_processamento(app, entradas):
    c = FilaController()
    c.adicionar([entradas])
    item = c.itens[0]
    item.estado = Estado.PROCESSANDO
    c.remover([item.id])
    assert item.id in [i.id for i in c.itens]


def test_pausar_impede_despacho(app, entradas, pasta):
    c = FilaController()
    c.definir_destino(pasta / "saida")
    c.adicionar([entradas])
    c.pausar()
    c.iniciar()
    assert all(i.estado is Estado.PENDENTE for i in c.itens)


def test_reordenar_muda_ordem(app, entradas):
    c = FilaController()
    c.adicionar([entradas])
    invertida = [i.id for i in reversed(c.itens)]
    c.reordenar(invertida)
    assert [i.id for i in c.itens] == invertida


def test_repetir_falhas_volta_para_pendente(app, entradas):
    c = FilaController()
    c.adicionar([entradas])
    c.itens[0].estado = Estado.FALHOU
    c.itens[0].mensagem = "erro antigo"
    c.repetir_falhas()
    assert c.itens[0].estado is Estado.PENDENTE
    assert c.itens[0].mensagem == ""


def test_limpar_preserva_item_em_processamento(app, entradas):
    c = FilaController()
    c.adicionar([entradas])
    c.itens[0].estado = Estado.PROCESSANDO
    c.limpar()
    assert len(c.itens) == 1


def test_conversao_ponta_a_ponta(app, entradas, pasta):
    """O teste que importa: 3 entradas viram 3 arquivos .md no destino."""
    destino = pasta / "saida"
    c = FilaController()
    c.definir_destino(destino)
    c.adicionar([entradas])

    espera = EsperaOcioso(c)
    c.iniciar()
    assert espera.esperar(30000), "a fila nao ficou ociosa em 30 segundos"

    gerados = sorted(p.name for p in destino.glob("*.md"))
    assert gerados == ["a_convertido.md", "b_convertido.md", "c_convertido.md"]
    assert all(i.estado is Estado.CONCLUIDO for i in c.itens)
    c.encerrar()


def test_nomes_nao_colidem_entre_workers(app, pasta):
    """Dois formatos com o mesmo nome base, convertidos em paralelo."""
    origem = pasta / "entrada"
    origem.mkdir()
    (origem / "doc.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (origem / "doc.json").write_text('{"a": 1}', encoding="utf-8")

    destino = pasta / "saida"
    c = FilaController()
    c.definir_destino(destino)
    c.adicionar([origem])

    espera = EsperaOcioso(c)
    c.iniciar()
    assert espera.esperar(30000)

    gerados = sorted(p.name for p in destino.glob("*.md"))
    assert gerados == ["doc_convertido (2).md", "doc_convertido.md"]
    c.encerrar()


def test_conversao_vazia_avisa_em_vez_de_calar(app, pasta):
    """Arquivo que nao rende texto nao pode passar por sucesso silencioso.

    Um PDF digitalizado e so imagem: o markitdown converte sem erro e
    devolve string vazia. Sem este aviso, o app grava um .md vazio, diz
    "Concluido" e o usuario so descobre ao abrir o arquivo. Para o publico
    deste app, que nao e tecnico, isso e pior do que uma falha honesta.
    """
    origem = pasta / "entrada"
    origem.mkdir()
    (origem / "vazio.txt").write_text("", encoding="utf-8")

    destino = pasta / "saida"
    c = FilaController()
    c.definir_destino(destino)
    c.adicionar([origem])

    espera = EsperaOcioso(c)
    c.iniciar()
    assert espera.esperar(30000)

    item = c.itens[0]
    assert item.estado is Estado.CONCLUIDO
    assert item.caracteres == 0
    assert item.mensagem, "conversao vazia precisa dizer alguma coisa"
    assert "texto" in item.mensagem.lower()
    c.encerrar()


def test_conversao_normal_nao_ganha_mensagem(app, entradas, pasta):
    """O aviso acima nao pode vazar para o caminho feliz."""
    destino = pasta / "saida"
    c = FilaController()
    c.definir_destino(destino)
    c.adicionar([entradas])

    espera = EsperaOcioso(c)
    c.iniciar()
    assert espera.esperar(30000)

    assert all(i.caracteres > 0 for i in c.itens)
    assert all(i.mensagem == "" for i in c.itens)
    c.encerrar()


def test_conversao_entra_no_historico(app, entradas, pasta):
    """O historico e alimentado pelo controller, que e quem sabe o desfecho."""
    from markitdown_gui.core.historico import Historico

    livro = Historico(pasta / "historico.db")
    destino = pasta / "saida"
    c = FilaController(historico=livro)
    c.definir_destino(destino)
    c.adicionar([entradas])

    espera = EsperaOcioso(c)
    c.iniciar()
    assert espera.esperar(30000)

    registros = livro.recentes()
    assert len(registros) == 3
    assert all(r.sucesso for r in registros)
    assert sorted(r.origem.name for r in registros) == ["a.csv", "b.csv", "c.csv"]
    assert all(r.caracteres > 0 for r in registros)
    c.encerrar()


def test_falha_tambem_entra_no_historico(app, pasta):
    from markitdown_gui.core.historico import Historico

    origem = pasta / "entrada"
    origem.mkdir()
    (origem / "ruim.pdf").write_bytes(b"%PDF-1.4\n" + b"\x00\xff" * 300)

    livro = Historico(pasta / "historico.db")
    c = FilaController(historico=livro)
    c.definir_destino(pasta / "saida")
    c.adicionar([origem])

    espera = EsperaOcioso(c)
    c.iniciar()
    assert espera.esperar(30000)

    (r,) = livro.recentes()
    assert r.sucesso is False
    assert r.mensagem
    c.encerrar()


def test_sem_historico_o_controller_funciona_igual(app, entradas, pasta):
    """O historico e opcional: passar None nao pode mudar nada."""
    destino = pasta / "saida"
    c = FilaController()
    c.definir_destino(destino)
    c.adicionar([entradas])

    espera = EsperaOcioso(c)
    c.iniciar()
    assert espera.esperar(30000)
    assert len(sorted(destino.glob("*.md"))) == 3
    c.encerrar()
