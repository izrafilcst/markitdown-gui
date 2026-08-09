"""Constroi o instalador: MarkItDown-Setup.exe.

Rodar da raiz do projeto:
    .venv\\Scripts\\python.exe -m installer.build_setup

O que ele faz, em ordem:

1. Garante que existe a versao em pasta do app, em `dist/MarkItDown`.
   Ela e a carga. A versao em arquivo unico nao serve: nesta maquina ela
   descompacta tudo e nunca abre janela, e um instalador que entrega um
   programa quebrado e pior do que nenhum instalador.
2. Comprime essa pasta em um zip.
3. Embute o zip dentro de um executavel unico, junto com o assistente.

O resultado e um arquivo so, que o usuario baixa, clica e instala.
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


def _versao() -> str:
    """Le a versao do proprio pacote do app, sem duplicar o numero."""
    sys.path.insert(0, str(RAIZ))
    try:
        from markitdown_gui import APP_VERSION

        return APP_VERSION
    except Exception:
        return "1.0.0"


def garantir_app_em_pasta() -> None:
    if (APP_EM_PASTA / "MarkItDown.exe").exists():
        print(f"usando o app ja construido em {APP_EM_PASTA}")
        return
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


def main() -> int:
    versao = _versao()
    print(f"construindo o instalador do MarkItDown {versao}")
    garantir_app_em_pasta()
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
