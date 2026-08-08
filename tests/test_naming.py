from pathlib import Path

import pytest

from markitdown_gui.core import naming


def test_sufixo_convertido():
    assert naming.output_filename(Path("livro_cavalos.pdf")) == "livro_cavalos_convertido.md"


def test_preserva_espaco_e_acento():
    assert naming.output_filename(Path("Relatorio 2024.docx")) == "Relatorio 2024_convertido.md"


def test_sem_colisao_usa_nome_limpo(pasta):
    destino = naming.resolve_output_path(Path("livro.pdf"), pasta)
    assert destino.name == "livro_convertido.md"


def test_colisao_com_arquivo_em_disco(pasta):
    (pasta / "livro_convertido.md").write_text("ja existe", encoding="utf-8")
    destino = naming.resolve_output_path(Path("livro.pdf"), pasta)
    assert destino.name == "livro_convertido (2).md"


def test_colisao_dentro_do_mesmo_lote(pasta):
    """livro.pdf e livro.docx na mesma fila querem o mesmo nome.

    Este e o caso que a checagem de disco sozinha nao pega, porque o
    primeiro arquivo ainda nao foi gravado quando o segundo e resolvido.
    """
    reservados = set()
    primeiro = naming.resolve_output_path(Path("livro.pdf"), pasta, reservados)
    reservados.add(primeiro)
    segundo = naming.resolve_output_path(Path("livro.docx"), pasta, reservados)

    assert primeiro.name == "livro_convertido.md"
    assert segundo.name == "livro_convertido (2).md"
    assert primeiro != segundo


def test_colisao_tripla(pasta):
    reservados = set()
    nomes = []
    for ext in (".pdf", ".docx", ".pptx"):
        caminho = naming.resolve_output_path(Path(f"a{ext}"), pasta, reservados)
        reservados.add(caminho)
        nomes.append(caminho.name)
    assert nomes == ["a_convertido.md", "a_convertido (2).md", "a_convertido (3).md"]


@pytest.mark.parametrize("bruto", ['a<b', 'a>b', 'a:b', 'a"b', 'a|b', 'a?b', 'a*b'])
def test_remove_caractere_invalido_do_windows(bruto):
    limpo = naming.sanitize_stem(bruto)
    assert not set(limpo) & set('<>:"/\\|?*')


def test_nome_reservado_do_windows():
    assert naming.sanitize_stem("CON") != "CON"
    assert naming.sanitize_stem("com1").lower() != "com1"


def test_nome_vazio_vira_placeholder():
    assert naming.sanitize_stem("   ") == "sem_nome"


def test_nome_muito_longo_e_cortado():
    assert len(naming.sanitize_stem("x" * 400)) <= 180
