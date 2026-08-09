"""Constroi o instalador: MarkItDown-Setup.exe.

Rodar da raiz do projeto:
    .venv\\Scripts\\python.exe -m installer.build_setup

Ha dois caminhos, e o script escolhe sozinho.

**Com Inno Setup instalado**, que e o preferido: sai um
`dist/MarkItDown-Setup.exe` de arquivo unico, com cerca de 83 MB, do
mesmo tipo que aplicativo comercial usa. Instala por usuario, sem pedir
administrador, cria atalhos, entra em Aplicativos Instalados e traz
desinstalador que devolve tambem o PATH.

**Sem Inno Setup**: sai um instalador em pasta, feito com PyInstaller,
mais a carga ao lado, zipados em `dist/MarkItDown-Setup.zip`. Funciona,
mas sao dois arquivos e o zip fica maior, porque o deflate do zipfile
comprime bem menos que o lzma2 do Inno.

Nos dois casos a carga e a versao em PASTA do app, `dist/MarkItDown`. A
versao do app em arquivo unico nao serve: nesta maquina ela descompacta
tudo e nunca abre janela, e um instalador que entrega um programa
quebrado e pior do que nenhum instalador.

Para instalar o Inno Setup:
    winget install --id JRSoftware.InnoSetup --exact
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist"
APP_EM_PASTA = DIST / "MarkItDown"
PACOTE = DIST / "MarkItDown-payload.zip"
VERSAO_TXT = DIST / "versao.txt"
PASTA_SETUP = DIST / "setup"
ZIP_FINAL = DIST / "MarkItDown-Setup.zip"
ISS_SAIDA = DIST


def _versao() -> str:
    """Le a versao do proprio pacote do app, sem duplicar o numero."""
    sys.path.insert(0, str(RAIZ))
    try:
        from markitdown_gui import APP_VERSION

        return APP_VERSION
    except Exception:
        return "1.0.0"


FONTES = ("markitdown_gui", "main.py")


def build_esta_obsoleto() -> bool:
    """Diz se o app empacotado e mais velho que o codigo fonte.

    Isto ja mordeu de verdade neste projeto: uma correcao de interface foi
    feita e commitada, o instalador foi gerado logo depois reaproveitando
    o `dist/MarkItDown` anterior, e o usuario recebeu o programa com o bug
    que acabara de ser consertado. Reaproveitar build e otimo; reaproveitar
    em silencio e armadilha.
    """
    exe = APP_EM_PASTA / "MarkItDown.exe"
    if not exe.exists():
        return True
    idade_do_build = exe.stat().st_mtime

    for nome in FONTES:
        alvo = RAIZ / nome
        if alvo.is_file():
            if alvo.stat().st_mtime > idade_do_build:
                return True
        elif alvo.is_dir():
            for caminho in alvo.rglob("*.py"):
                if caminho.stat().st_mtime > idade_do_build:
                    return True
    return False


def garantir_app_em_pasta() -> None:
    if (APP_EM_PASTA / "MarkItDown.exe").exists():
        if not build_esta_obsoleto():
            print(f"usando o app ja construido em {APP_EM_PASTA}")
            return
        print("o codigo mudou depois do ultimo build do app, reconstruindo")
    else:
        print("app em pasta nao encontrado, construindo antes")
    sys.path.insert(0, str(RAIZ))
    import build

    codigo = build.empacotar(arquivo_unico=False)
    if codigo != 0:
        raise SystemExit(f"a construcao do app falhou com codigo {codigo}")


def comprimir() -> Path:
    """Zipa a pasta do app, guardando caminhos relativos a ela."""
    if PACOTE.exists():
        PACOTE.unlink()
    total = 0
    bytes_crus = 0
    with zipfile.ZipFile(PACOTE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for caminho in sorted(APP_EM_PASTA.rglob("*")):
            if caminho.is_file():
                z.write(caminho, caminho.relative_to(APP_EM_PASTA).as_posix())
                total += 1
                bytes_crus += caminho.stat().st_size
    comprimido = PACOTE.stat().st_size
    print(
        f"pacote: {total} arquivos, "
        f"{bytes_crus / 1024 / 1024:.0f} MB crus, "
        f"{comprimido / 1024 / 1024:.0f} MB comprimidos"
    )
    return PACOTE


def empacotar_instalador(versao: str) -> int:
    """Gera o instalador em pasta, com a carga ao lado.

    Duas decisoes aqui vieram de medicao, nao de preferencia.

    A carga fica FORA do executavel porque embutir 116 MB faz o bootloader
    do PyInstaller travar no meio da descompactacao: para em 984 arquivos e
    140 MB, CPU parada, processo vivo, nada na tela.

    O instalador e em pasta e nao em arquivo unico porque, nesta maquina,
    onefile em modo janela nao abre janela nenhuma nem com 11 MB, embora o
    mesmo assistente rodando do codigo funcione perfeitamente. Modo pasta
    funciona em todos os casos testados, inclusive para o proprio app.
    """
    VERSAO_TXT.write_text(versao, encoding="utf-8")
    PASTA_SETUP.mkdir(parents=True, exist_ok=True)

    separador = ";" if os.name == "nt" else ":"
    comando = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        "MarkItDown-Setup",
        "--distpath",
        str(PASTA_SETUP),
        "--workpath",
        str(RAIZ / "build" / "setup"),
        "--specpath",
        str(RAIZ / "build"),
        "--paths",
        str(RAIZ),
        "--add-data",
        f"{VERSAO_TXT}{separador}.",
        "--icon",
        str(RAIZ / "resources" / "icone.ico"),
        str(RAIZ / "installer" / "entrada.py"),
    ]
    print("rodando:", " ".join(comando))
    codigo = subprocess.run(comando, cwd=RAIZ, check=False).returncode
    if codigo == 0:
        shutil.copy2(PACOTE, PASTA_SETUP / "MarkItDown-Setup" / PACOTE.name)
    return codigo


def zipar_para_distribuir() -> Path:
    """Junta instalador e carga num zip so, que e o que o usuario baixa."""
    if ZIP_FINAL.exists():
        ZIP_FINAL.unlink()
    with zipfile.ZipFile(ZIP_FINAL, "w", zipfile.ZIP_STORED) as z:
        # ZIP_STORED e nao DEFLATED: a carga ja esta comprimida, e comprimir
        # de novo gastaria minutos para economizar quase nada.
        for caminho in sorted(PASTA_SETUP.rglob("*")):
            if caminho.is_file():
                z.write(caminho, caminho.relative_to(PASTA_SETUP).as_posix())
    return ZIP_FINAL


def achar_iscc() -> Path | None:
    """Localiza o compilador do Inno Setup, se estiver instalado."""
    candidatos = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"
        / "Inno Setup 6" / "ISCC.exe",
    ]
    for caminho in candidatos:
        if caminho.exists():
            return caminho
    return None


LIMITE_DO_WINDOWS = 260


def limite_da_pasta_de_destino() -> int:
    """Quantos caracteres a pasta de destino pode ter, sem estourar.

    Calculado da carga real, e nao chutado: se um dia entrar uma
    dependencia com caminho ainda mais fundo que o lxml, o instalador
    passa a recusar destinos mais curtos automaticamente, em vez de
    quebrar no meio da copia.
    """
    maior = 0
    for caminho in APP_EM_PASTA.rglob("*"):
        if caminho.is_file():
            maior = max(maior, len(str(caminho.relative_to(APP_EM_PASTA))))
    # Um caractere para a barra que separa a pasta do arquivo.
    return LIMITE_DO_WINDOWS - maior - 1


def empacotar_com_inno(versao: str, iscc: Path) -> int:
    """Gera um Setup.exe unico e de verdade, com o Inno Setup.

    E o mecanismo que aplicativo comercial usa. Diferente do executavel
    unico do PyInstaller, ele nao descompacta o programa inteiro no
    temporario para depois executar: grava direto na pasta de destino, o
    que e justamente o passo que trava aqui.
    """
    ISS_SAIDA.mkdir(parents=True, exist_ok=True)
    limite = limite_da_pasta_de_destino()
    print(f"pasta de destino pode ter ate {limite} caracteres")
    comando = [
        str(iscc),
        f"/DVersao={versao}",
        f"/DLimitePasta={limite}",
        f"/DCarga={APP_EM_PASTA}",
        f"/DIcone={RAIZ / 'resources' / 'icone.ico'}",
        f"/DSaida={ISS_SAIDA}",
        str(RAIZ / "installer" / "markitdown.iss"),
    ]
    print("rodando:", " ".join(comando))
    return subprocess.run(comando, cwd=RAIZ, check=False).returncode


def main() -> int:
    versao = _versao()
    print(f"construindo o instalador do MarkItDown {versao}")
    garantir_app_em_pasta()

    iscc = achar_iscc()
    if iscc is not None:
        print(f"Inno Setup encontrado: {iscc}")
        codigo = empacotar_com_inno(versao, iscc)
        alvo = ISS_SAIDA / "MarkItDown-Setup.exe"
        if codigo == 0 and alvo.exists():
            mb = alvo.stat().st_size / 1024 / 1024
            print()
            print(f"pronto: {alvo} ({mb:.0f} MB), um arquivo so")
            return 0
        print("a compilacao com Inno Setup falhou, caindo para o modo em pasta")
    else:
        print("Inno Setup nao encontrado, gerando o instalador em pasta")

    comprimir()
    codigo = empacotar_instalador(versao)
    if codigo != 0:
        return codigo

    exe = PASTA_SETUP / "MarkItDown-Setup" / "MarkItDown-Setup.exe"
    zipado = zipar_para_distribuir()
    print()
    print(f"instalador : {exe} ({exe.stat().st_size / 1024 / 1024:.0f} MB)")
    print(f"carga      : {(exe.parent / PACOTE.name).stat().st_size / 1024 / 1024:.0f} MB")
    print(f"para enviar: {zipado} ({zipado.stat().st_size / 1024 / 1024:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
