import socket
from pathlib import Path

import pytest

from markitdown_gui.core import converter

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def rede_bloqueada(monkeypatch):
    """Qualquer tentativa de abrir socket vira falha de teste."""

    def proibido(*args, **kwargs):
        raise AssertionError("O app tentou usar a rede. Isso viola a decisao 4 do projeto.")

    monkeypatch.setattr(socket, "socket", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)
    return True


@pytest.mark.parametrize("nome", ["exemplo.html", "exemplo.csv", "exemplo.json"])
def test_converte_sem_tocar_a_rede(rede_bloqueada, nome):
    resultado = converter.converter(FIXTURES / nome)
    assert resultado.caracteres > 0
    assert isinstance(resultado.markdown, str)


def test_arquivo_inexistente_da_mensagem_humana():
    with pytest.raises(converter.ErroDeConversao) as exc:
        converter.converter(Path("nao_existe_mesmo.pdf"))
    # A mensagem vai para a tela: nao pode conter nome de excecao Python.
    assert "Exception" not in exc.value.mensagem
    assert "Error" not in exc.value.mensagem


def test_gravar_em_pasta_sem_permissao(pasta, monkeypatch):
    def negar(*args, **kwargs):
        raise PermissionError("negado")

    monkeypatch.setattr(Path, "write_text", negar)
    with pytest.raises(converter.ErroDeConversao) as exc:
        converter.gravar("conteudo", pasta / "saida.md")
    assert "permissao" in exc.value.mensagem.lower()


def test_nenhum_import_de_rede_no_pacote():
    """Varredura estatica: o codigo nao pode nem mencionar cliente HTTP."""
    import re

    raiz = Path(__file__).parent.parent / "markitdown_gui"
    proibidos = re.compile(r"\b(requests|urllib|httpx|aiohttp|api_key|endpoint)\b")
    ofensores = []
    for py in raiz.rglob("*.py"):
        texto = py.read_text(encoding="utf-8")
        if proibidos.search(texto):
            ofensores.append(py.name)
    assert ofensores == [], f"Referencia a rede encontrada em: {ofensores}"


def test_core_nao_importa_qt():
    raiz = Path(__file__).parent.parent / "markitdown_gui" / "core"
    ofensores = [
        py.name for py in raiz.rglob("*.py")
        if "from PySide6" in py.read_text(encoding="utf-8")
        or "import PySide6" in py.read_text(encoding="utf-8")
    ]
    assert ofensores == [], f"Qt vazou para o core em: {ofensores}"
