"""Testes da logica do instalador.

O que esta aqui e o que mexe no computador de quem instala: PATH, pastas
e conferencia de integridade. Errar em qualquer um desses estraga a
maquina do usuario de um jeito que ele nao sabe desfazer, entao cada um
tem teste.

Nada aqui abre janela, escreve no registro de verdade nem toca no PATH
real: a logica foi separada da interface exatamente para isso.
"""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from installer import nucleo  # noqa: E402


# ------------------------------------------------------------ destino

def test_destino_padrao_fica_na_pasta_do_usuario(pasta):
    destino = nucleo.destino_padrao(base=pasta)
    assert destino == pasta / "Programs" / "MarkItDown"


def test_destino_padrao_usa_localappdata(monkeypatch, pasta):
    monkeypatch.setenv("LOCALAPPDATA", str(pasta))
    assert nucleo.destino_padrao() == pasta / "Programs" / "MarkItDown"


def test_destino_padrao_sem_localappdata_nao_estoura(monkeypatch):
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    destino = nucleo.destino_padrao()
    assert destino.is_absolute()
    assert destino.name == "MarkItDown"


# ------------------------------------------------------- destino seguro

def test_recusa_raiz_de_disco():
    assert nucleo.destino_seguro(Path("C:/")) is False


def test_recusa_caminho_relativo():
    assert nucleo.destino_seguro(Path("MarkItDown")) is False


def test_recusa_a_pasta_pessoal():
    assert nucleo.destino_seguro(Path.home()) is False


def test_recusa_pasta_cheia_de_outra_coisa(pasta):
    alvo = pasta / "documentos_do_usuario"
    alvo.mkdir()
    (alvo / "tese.docx").write_text("nao me apague", encoding="utf-8")
    assert nucleo.destino_seguro(alvo) is False


def test_aceita_pasta_vazia(pasta):
    alvo = pasta / "vazia"
    alvo.mkdir()
    assert nucleo.destino_seguro(alvo) is True


def test_aceita_pasta_que_nao_existe_ainda(pasta):
    assert nucleo.destino_seguro(pasta / "nova" / "MarkItDown") is True


def test_aceita_reinstalacao_por_cima(pasta):
    """Pasta com instalacao anterior nossa pode ser sobrescrita."""
    alvo = pasta / "MarkItDown"
    alvo.mkdir()
    (alvo / nucleo.EXECUTAVEL).write_bytes(b"exe antigo")
    (alvo / "sobra.txt").write_text("de antes", encoding="utf-8")
    assert nucleo.destino_seguro(alvo) is True


def test_recusa_arquivo_como_destino(pasta):
    alvo = pasta / "isso_e_um_arquivo"
    alvo.write_text("x", encoding="utf-8")
    assert nucleo.destino_seguro(alvo) is False


# --------------------------------------------------------------- PATH

def test_acrescenta_ao_path(pasta):
    novo = nucleo.path_com(r"C:\Windows;C:\Windows\System32", pasta)
    assert str(pasta) in nucleo.entradas_do_path(novo)


def test_nao_duplica_no_path(pasta):
    uma_vez = nucleo.path_com("C:\\Windows", pasta)
    duas_vezes = nucleo.path_com(uma_vez, pasta)
    assert nucleo.entradas_do_path(duas_vezes).count(str(pasta)) == 1


def test_nao_duplica_com_barra_final_ou_caixa_diferente():
    """Reinstalar nao pode inchar o PATH com variacoes do mesmo caminho."""
    base = r"C:\Users\Fulano\Programs\MarkItDown"
    valor = f"C:\\Windows;{base}\\"
    resultado = nucleo.path_com(valor, Path(base.lower()))
    assert len(nucleo.entradas_do_path(resultado)) == 2


def test_remove_do_path(pasta):
    com = nucleo.path_com("C:\\Windows", pasta)
    sem = nucleo.path_sem(com, pasta)
    assert str(pasta) not in nucleo.entradas_do_path(sem)
    assert "C:\\Windows" in nucleo.entradas_do_path(sem)


def test_remove_do_path_tolera_barra_e_caixa():
    base = r"C:\Programs\MarkItDown"
    valor = f"C:\\Windows;{base}\\;C:\\Outro"
    sem = nucleo.path_sem(valor, Path(base.upper()))
    assert nucleo.entradas_do_path(sem) == ["C:\\Windows", "C:\\Outro"]


def test_path_vazio_nao_gera_entrada_fantasma(pasta):
    resultado = nucleo.path_com("", pasta)
    assert nucleo.entradas_do_path(resultado) == [str(pasta)]


def test_remover_de_path_que_nao_tem_nao_muda_nada(pasta):
    valor = "C:\\Windows;C:\\Outro"
    assert nucleo.path_sem(valor, pasta) == valor


# -------------------------------------------------------- verificacao

def _instalacao_completa(destino: Path) -> None:
    for alvo in nucleo.ESSENCIAIS:
        caminho = destino / alvo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(b"conteudo de mentira")


def test_instalacao_completa_passa(pasta):
    destino = pasta / "app"
    _instalacao_completa(destino)
    r = nucleo.verificar(destino)
    assert r.completa is True
    assert r.faltando == ()
    assert r.arquivos == len(nucleo.ESSENCIAIS)


def test_pasta_inexistente_reprova(pasta):
    r = nucleo.verificar(pasta / "nunca_instalado")
    assert r.completa is False
    assert nucleo.EXECUTAVEL in r.faltando


@pytest.mark.parametrize("ausente", nucleo.ESSENCIAIS)
def test_falta_de_qualquer_essencial_reprova(pasta, ausente):
    """Cada arquivo da lista precisa realmente derrubar a verificacao."""
    destino = pasta / "app"
    _instalacao_completa(destino)
    (destino / ausente).unlink()

    r = nucleo.verificar(destino)
    assert r.completa is False
    assert ausente in r.faltando
    assert ausente in r.resumo


def test_pasta_vazia_reprova(pasta):
    destino = pasta / "app"
    destino.mkdir()
    assert nucleo.verificar(destino).completa is False


def test_resumo_de_instalacao_boa_fala_de_tamanho(pasta):
    destino = pasta / "app"
    _instalacao_completa(destino)
    assert "arquivos" in nucleo.verificar(destino).resumo


# ------------------------------------------------------------ extracao

def test_extrai_tudo_e_avisa_o_progresso(pasta):
    pacote = pasta / "carga.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("MarkItDown.exe", "binario")
        z.writestr("_internal/base_library.zip", "biblioteca")
        z.writestr("_internal/sub/outro.dll", "dll")

    destino = pasta / "instalado"
    vistos = []
    total = nucleo.extrair(pacote, destino, progresso=lambda f, t: vistos.append((f, t)))

    assert total == 3
    assert (destino / "MarkItDown.exe").exists()
    assert (destino / "_internal" / "sub" / "outro.dll").exists()
    assert vistos[0] == (1, 3) and vistos[-1] == (3, 3)


def test_extrai_para_pasta_que_nao_existe(pasta):
    pacote = pasta / "carga.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("MarkItDown.exe", "binario")

    destino = pasta / "nova" / "profunda" / "MarkItDown"
    nucleo.extrair(pacote, destino)
    assert (destino / "MarkItDown.exe").exists()


def test_extrair_sem_callback_funciona(pasta):
    pacote = pasta / "carga.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("a.txt", "x")
    assert nucleo.extrair(pacote, pasta / "saida") == 1


def test_separador_do_path_e_o_do_sistema():
    """entradas_do_path precisa usar o separador real, nao um chute."""
    valor = os.pathsep.join(["A", "B"])
    assert nucleo.entradas_do_path(valor) == ["A", "B"]


# ------------------------------------------------------ caminhos longos

def test_prefixo_de_caminho_longo_no_windows():
    """O Windows corta caminho em 260 caracteres, e o prefixo escapa disso."""
    if os.name != "nt":
        pytest.skip("regra de caminho longo so existe no Windows")
    # Montado por partes de proposito: escrever o prefixo como literal
    # escapado e a forma mais facil de errar de todas.
    prefixo = 2 * chr(92) + "?" + chr(92)
    bruto = nucleo.caminho_longo(Path(r"C:\Users\Fulano\Programs\MarkItDown"))
    assert bruto.startswith(prefixo), f"prefixo ausente em {bruto!r}"
    assert bruto.endswith(r"Users\Fulano\Programs\MarkItDown")


def test_prefixo_nao_e_aplicado_duas_vezes():
    if os.name != "nt":
        pytest.skip("regra de caminho longo so existe no Windows")
    prefixo = 2 * chr(92) + "?" + chr(92)
    uma = nucleo.caminho_longo(Path(r"C:\App"))
    duas = nucleo.caminho_longo(Path(uma))
    assert duas.count(prefixo) == 1, f"prefixo duplicado em {duas!r}"


def test_extrai_caminho_maior_que_260_caracteres(pasta):
    """A carga real tem caminhos fundos, por causa do lxml empacotado.

    Sem o prefixo de caminho longo, a instalacao morre no meio com
    FileNotFoundError, deixando o programa pela metade. Aconteceu de
    verdade neste projeto, com o lxml/isoschematron.
    """
    fundo = "/".join(["pasta_com_nome_bem_comprido"] * 6)
    interno = f"_internal/{fundo}/iso_schematron_skeleton_for_xslt1.xsl"

    pacote = pasta / "carga.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("MarkItDown.exe", "binario")
        z.writestr(interno, "conteudo profundo")

    destino = pasta / ("d" * 60) / ("e" * 60) / "MarkItDown"
    nucleo.extrair(pacote, destino)

    alvo = destino / Path(interno)
    assert len(str(alvo)) > 260, f"o teste precisa passar de 260: {len(str(alvo))}"
    assert nucleo.existe(alvo), "arquivo fundo nao foi gravado"


def test_verificar_funciona_em_caminho_longo(pasta):
    destino = pasta / ("f" * 70) / ("g" * 70) / "MarkItDown"
    for alvo in nucleo.ESSENCIAIS:
        caminho = destino / alvo
        nucleo.criar_pastas(caminho.parent)
        nucleo.gravar_bytes(caminho, b"x")
    assert nucleo.verificar(destino).completa is True


# ------------------------------------------------- frescor da construcao

def test_build_obsoleto_e_detectado(pasta, monkeypatch):
    """Fonte mais nova que o executavel significa build velho.

    Isto ja mordeu de verdade: o instalador foi gerado reaproveitando um
    app construido antes de uma correcao de interface, e entregou ao
    usuario a versao com o bug que acabara de ser consertado. Reaproveitar
    e otimo, desde que nao seja em silencio.
    """
    from installer import build_setup

    app = pasta / "dist" / "MarkItDown"
    app.mkdir(parents=True)
    exe = app / "MarkItDown.exe"
    exe.write_bytes(b"binario")

    fonte = pasta / "markitdown_gui" / "ui" / "queue_row.py"
    fonte.parent.mkdir(parents=True)
    fonte.write_text("codigo novo", encoding="utf-8")
    import os
    import time

    os.utime(fonte, (time.time() + 60, time.time() + 60))

    monkeypatch.setattr(build_setup, "RAIZ", pasta)
    monkeypatch.setattr(build_setup, "APP_EM_PASTA", app)
    assert build_setup.build_esta_obsoleto() is True


def test_build_atual_nao_e_reconstruido(pasta, monkeypatch):
    from installer import build_setup
    import os
    import time

    app = pasta / "dist" / "MarkItDown"
    app.mkdir(parents=True)
    exe = app / "MarkItDown.exe"

    fonte = pasta / "markitdown_gui" / "ui" / "queue_row.py"
    fonte.parent.mkdir(parents=True)
    fonte.write_text("codigo", encoding="utf-8")
    exe.write_bytes(b"binario")
    os.utime(exe, (time.time() + 60, time.time() + 60))

    monkeypatch.setattr(build_setup, "RAIZ", pasta)
    monkeypatch.setattr(build_setup, "APP_EM_PASTA", app)
    assert build_setup.build_esta_obsoleto() is False


def test_sem_build_nenhum_conta_como_obsoleto(pasta, monkeypatch):
    from installer import build_setup

    monkeypatch.setattr(build_setup, "RAIZ", pasta)
    monkeypatch.setattr(build_setup, "APP_EM_PASTA", pasta / "nao_existe")
    assert build_setup.build_esta_obsoleto() is True
