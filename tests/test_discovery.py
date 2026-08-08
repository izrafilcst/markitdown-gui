from pathlib import Path

from markitdown_gui.core import discovery, formats


def _criar(pasta: Path, *nomes: str) -> list[Path]:
    criados = []
    for nome in nomes:
        alvo = pasta / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text("conteudo", encoding="utf-8")
        criados.append(alvo)
    return criados


def test_arquivo_suportado_entra(pasta):
    (arquivo,) = _criar(pasta, "a.pdf")
    r = discovery.expandir([arquivo])
    assert r.aceitos == [arquivo.resolve()]
    assert r.recusados == []


def test_arquivo_nao_suportado_recusado_com_motivo(pasta):
    (arquivo,) = _criar(pasta, "a.exe")
    r = discovery.expandir([arquivo])
    assert r.aceitos == []
    assert len(r.recusados) == 1
    assert r.recusados[0].motivo


def test_imagem_recusada_explica_porque(pasta):
    (arquivo,) = _criar(pasta, "foto.png")
    r = discovery.expandir([arquivo])
    assert "online" in r.recusados[0].motivo.lower()


def test_pasta_expande_recursivamente(pasta):
    _criar(pasta, "raiz.pdf", "sub/meio.docx", "sub/mais/fundo.pptx", "sub/ignorar.exe")
    r = discovery.expandir([pasta])
    nomes = sorted(p.name for p in r.aceitos)
    assert nomes == ["fundo.pptx", "meio.docx", "raiz.pdf"]


def test_ruido_dentro_de_pasta_nao_polui_recusados(pasta):
    """Arquivo irrelevante achado varrendo pasta nao vira aviso.

    Solto direto pelo usuario e sinal de intencao e merece explicacao.
    Achado varrendo uma pasta e so ruido.
    """
    _criar(pasta, "bom.pdf", "ruido.exe", "outro.dll")
    r = discovery.expandir([pasta])
    assert len(r.aceitos) == 1
    assert r.recusados == []


def test_pasta_sem_nada_convertivel_avisa(pasta):
    _criar(pasta, "a.exe", "b.dll")
    r = discovery.expandir([pasta])
    assert r.aceitos == []
    assert len(r.recusados) == 1
    assert "pasta" in r.recusados[0].motivo.lower()


def test_duplicata_no_mesmo_drop(pasta):
    (arquivo,) = _criar(pasta, "a.pdf")
    r = discovery.expandir([arquivo, arquivo])
    assert len(r.aceitos) == 1


def test_ja_na_fila_nao_repete(pasta):
    (arquivo,) = _criar(pasta, "a.pdf")
    r = discovery.expandir([arquivo], ja_na_fila={arquivo.resolve()})
    assert r.aceitos == []


def test_arquivo_inexistente(pasta):
    r = discovery.expandir([pasta / "fantasma.pdf"])
    assert r.aceitos == []
    assert "movido" in r.recusados[0].motivo.lower()


def test_pasta_oculta_ignorada(pasta):
    _criar(pasta, "visivel.pdf", ".oculta/escondido.pdf")
    r = discovery.expandir([pasta])
    assert [p.name for p in r.aceitos] == ["visivel.pdf"]


def test_teto_de_arquivos(pasta, monkeypatch):
    monkeypatch.setattr(formats, "MAX_ARQUIVOS", 3)
    _criar(pasta, *[f"a{i}.pdf" for i in range(10)])
    r = discovery.expandir([pasta])
    assert len(r.aceitos) == 3
    assert r.truncado is True
