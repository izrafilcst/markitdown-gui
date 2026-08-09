"""Integracao com o Windows: PATH, atalhos e Programas e Recursos.

Esta camada e deliberadamente burra. Toda decisao vive em `nucleo.py`,
que e testavel; aqui so ficam as chamadas que mexem de verdade no sistema
e que por isso nao dao para exercitar em teste sem estragar a maquina de
quem roda a suite.

Tudo acontece em HKCU e na pasta do usuario. Nada pede administrador.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import nucleo

CHAVE_AMBIENTE = "Environment"


# ------------------------------------------------------------------ PATH

def _abrir_ambiente(escrita: bool):
    import winreg

    acesso = winreg.KEY_READ | (winreg.KEY_WRITE if escrita else 0)
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_AMBIENTE, 0, acesso)


def ler_path_do_usuario() -> str:
    import winreg

    try:
        with _abrir_ambiente(escrita=False) as chave:
            valor, _ = winreg.QueryValueEx(chave, "Path")
            return str(valor)
    except FileNotFoundError:
        return ""


def _gravar_path_do_usuario(valor: str) -> None:
    import winreg

    with _abrir_ambiente(escrita=True) as chave:
        # REG_EXPAND_SZ e nao REG_SZ: o PATH do usuario costuma conter
        # %USERPROFILE% e afins, e gravar como REG_SZ congelaria essas
        # variaveis, quebrando entradas de outros programas.
        winreg.SetValueEx(chave, "Path", 0, winreg.REG_EXPAND_SZ, valor)
    _avisar_o_sistema()


def _avisar_o_sistema() -> None:
    """Faz o Windows reler o ambiente sem precisar reiniciar a sessao.

    Sem esta transmissao, o PATH novo so aparece depois de sair e entrar
    na conta, e o usuario conclui que o instalador nao funcionou.
    """
    try:
        import ctypes
        from ctypes import wintypes

        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        resultado = wintypes.DWORD()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            ctypes.c_wchar_p("Environment"),
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(resultado),
        )
    except Exception:
        # Falhar aqui nao invalida a instalacao: o PATH ja foi gravado e
        # vale na proxima sessao. Nao vale derrubar o instalador por isso.
        pass


def acrescentar_ao_path(pasta: Path) -> None:
    atual = ler_path_do_usuario()
    novo = nucleo.path_com(atual, pasta)
    if novo != atual:
        _gravar_path_do_usuario(novo)


def remover_do_path(pasta: Path) -> None:
    atual = ler_path_do_usuario()
    novo = nucleo.path_sem(atual, pasta)
    if novo != atual:
        _gravar_path_do_usuario(novo)


# --------------------------------------------------------------- atalhos

def _powershell(script: str) -> bool:
    try:
        concluido = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return concluido.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def criar_atalho(destino_lnk: Path, alvo: Path, icone: Path | None = None) -> bool:
    """Cria um .lnk usando o proprio Windows.

    Via PowerShell e WScript.Shell, e nao via pywin32, para nao arrastar
    uma dependencia inteira para dentro do instalador so por causa disto.
    """
    destino_lnk.parent.mkdir(parents=True, exist_ok=True)
    icone_linha = (
        f"$a.IconLocation = '{icone}';" if icone is not None else ""
    )
    script = (
        "$s = New-Object -ComObject WScript.Shell;"
        f"$a = $s.CreateShortcut('{destino_lnk}');"
        f"$a.TargetPath = '{alvo}';"
        f"$a.WorkingDirectory = '{alvo.parent}';"
        f"$a.Description = 'Converte documentos para Markdown';"
        f"{icone_linha}"
        "$a.Save()"
    )
    return _powershell(script) and destino_lnk.exists()


def pasta_menu_iniciar() -> Path:
    base = os.environ.get("APPDATA")
    raiz = Path(base) if base else Path.home() / "AppData" / "Roaming"
    return raiz / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def pasta_area_de_trabalho() -> Path:
    perfil = Path(os.environ.get("USERPROFILE", str(Path.home())))
    for nome in ("Desktop", "Area de Trabalho"):
        alvo = perfil / nome
        if alvo.is_dir():
            return alvo
    return perfil / "Desktop"


# ------------------------------------------- Programas e Recursos (HKCU)

def registrar_desinstalacao(destino: Path, versao: str, tamanho_kb: int) -> bool:
    """Faz o programa aparecer em Aplicativos Instalados do Windows.

    Sem isto o usuario nao tem como remover pelo caminho normal, e um
    programa que so se desinstala apagando pasta na mao e um programa mal
    educado.
    """
    try:
        import winreg

        desinstalador = destino / "desinstalar.cmd"
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, nucleo.CHAVE_DESINSTALACAO
        ) as chave:
            valores = {
                "DisplayName": nucleo.APP,
                "DisplayVersion": versao,
                "Publisher": nucleo.APP,
                "InstallLocation": str(destino),
                "DisplayIcon": str(destino / nucleo.EXECUTAVEL),
                "UninstallString": f'"{desinstalador}"',
                "NoModify": None,
                "NoRepair": None,
                "EstimatedSize": None,
            }
            for nome, valor in valores.items():
                if valor is None:
                    continue
                winreg.SetValueEx(chave, nome, 0, winreg.REG_SZ, valor)
            for nome, numero in (
                ("NoModify", 1),
                ("NoRepair", 1),
                ("EstimatedSize", tamanho_kb),
            ):
                winreg.SetValueEx(chave, nome, 0, winreg.REG_DWORD, numero)
        return True
    except OSError:
        return False


def remover_registro_de_desinstalacao() -> bool:
    try:
        import winreg

        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, nucleo.CHAVE_DESINSTALACAO)
        return True
    except OSError:
        return False


def escrever_desinstalador(
    destino: Path, atalhos: list[Path], mexeu_no_path: bool
) -> Path:
    """Grava um .cmd que desfaz exatamente o que foi feito.

    Um arquivo de lote, e nao um segundo executavel, porque o instalador
    ja tem mais de cem megabytes e copiar tudo de novo so para poder
    desinstalar seria absurdo. O lote chama o PowerShell para as partes
    que precisam mexer no registro.
    """
    linhas = [
        "@echo off",
        "setlocal",
        f'echo Removendo {nucleo.APP}...',
        "",
    ]
    for atalho in atalhos:
        linhas.append(f'if exist "{atalho}" del /f /q "{atalho}"')

    limpeza = [
        "$ErrorActionPreference = 'SilentlyContinue';",
        f"Remove-Item -Path 'HKCU:\\{nucleo.CHAVE_DESINSTALACAO}' "
        "-Recurse -Force;",
    ]
    if mexeu_no_path:
        limpeza.append(
            "$p = [Environment]::GetEnvironmentVariable('Path','User');"
            f"$alvo = '{destino}';"
            "$partes = $p -split ';' | Where-Object "
            "{ $_ -and ($_.TrimEnd('\\') -ne $alvo.TrimEnd('\\')) };"
            "[Environment]::SetEnvironmentVariable("
            "'Path', ($partes -join ';'), 'User');"
        )
    linhas.append(
        'powershell -NoProfile -ExecutionPolicy Bypass -Command "'
        + " ".join(limpeza).replace('"', "'")
        + '"'
    )

    # A pasta e apagada por ultimo, de dentro do temporario, porque o
    # proprio .cmd mora nela e nao da para apagar o chao sob os pes.
    linhas += [
        "",
        'set "ALVO=%~dp0"',
        'cd /d "%TEMP%"',
        'timeout /t 1 /nobreak >nul',
        'rmdir /s /q "%ALVO%"',
        f'echo {nucleo.APP} removido.',
        "",
    ]

    caminho = destino / "desinstalar.cmd"
    caminho.write_text("\r\n".join(linhas), encoding="ascii", errors="replace")
    return caminho


def abrir(caminho: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(caminho))  # noqa: S606
        else:
            subprocess.run(["xdg-open", str(caminho)], check=False)
    except OSError:
        pass
