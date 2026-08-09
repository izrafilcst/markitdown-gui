"""Empacotamento do MarkItDown em um .exe autocontido.

Rodar: .venv\\Scripts\\python.exe build.py

Duas armadilhas conhecidas, e as duas vem da deteccao de tipo de arquivo
que o markitdown usa por baixo:

1. `magika` carrega um modelo de rede neural que fica em arquivos de dados
   do pacote. O PyInstaller nao segue dado, so import, entao sem
   `--collect-data magika` o .exe monta e quebra na primeira conversao.
2. `onnxruntime` traz DLLs nativas que o analisador tambem nao enxerga,
   dai o `--collect-binaries onnxruntime`.
3. `numpy` 2.x reorganizou o pacote em `numpy._core`, e a versao instalada
   aqui (2.5.1) e mais nova que os hooks que o PyInstaller traz de fabrica.
   Sem `--collect-all numpy`, o .exe monta sem reclamar e morre no import
   com "No module named 'numpy._core._exceptions'", antes de abrir janela.
   Este foi um erro real, pego rodando o .exe com o PATH limpo.

O resultado esperado fica na faixa de 150 a 250 MB, quase tudo modelo e
runtime nativo. Isso e o preco de detectar tipo de arquivo sem consultar
servico online, e foi uma escolha deliberada do projeto.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
RECURSOS = RAIZ / "resources"
ICONE = RECURSOS / "icone.ico"

TAMANHOS = (16, 24, 32, 48, 64, 128, 256)


def gerar_icone() -> Path:
    """Desenha o icone do app a partir dos proprios tokens de design.

    Nada de arquivo de imagem vindo de fora: o icone sai das mesmas cores
    e do mesmo desenho que a interface usa, entao ele nunca fica fora de
    sincronia com o tema.
    """
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    from markitdown_gui.ui import icons, theme

    app = QApplication.instance() or QApplication([])
    del app

    RECURSOS.mkdir(parents=True, exist_ok=True)
    quadros = []
    for lado in TAMANHOS:
        imagem = QImage(lado, lado, QImage.Format.Format_ARGB32)
        imagem.fill(Qt.GlobalColor.transparent)

        pintor = QPainter(imagem)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QBrush(QColor(theme.COLOR["primary"])))
        raio = lado * 0.22
        pintor.drawRoundedRect(QRectF(0, 0, lado, lado), raio, raio)

        glifo = max(8, int(lado * 0.56))
        # escala=1.0 e obrigatorio aqui: o padrao segue o devicePixelRatio
        # da tela, o que e certo para a interface e errado para um arquivo.
        # Sem isso o mesmo comando produz um .ico diferente em cada monitor,
        # e o build suja a arvore de trabalho a cada execucao.
        marca = icons.pixmap(
            "arquivo", theme.COLOR["on_primary"], glifo, escala=1.0
        )
        pintor.drawPixmap(
            int((lado - marca.width()) / 2),
            int((lado - marca.height()) / 2),
            marca,
        )
        pintor.end()
        quadros.append(imagem)

    maior = quadros[-1]
    if not maior.save(str(ICONE), "ICO"):
        raise SystemExit(f"Nao foi possivel gravar {ICONE}")
    print(f"icone gerado: {ICONE}")
    return ICONE


def empacotar(arquivo_unico: bool = False) -> int:
    """Empacota em pasta (padrao) ou em um executavel unico.

    A diferenca importa para quem vai receber o programa:

    Pasta (`onedir`): sai `dist/MarkItDown/`, com o .exe e a pasta
    `_internal` ao lado. Abre rapido, porque nada e descompactado. O .exe
    NAO funciona sozinho, entao a pasta inteira precisa ser distribuida.

    Arquivo unico (`onefile`): sai `dist/MarkItDown.exe`, um arquivo so.
    ATENCAO, medido nesta maquina: ele NAO ABRE. A descompactacao para no
    meio, em torno de 140 MB, a CPU fica parada e o processo segue vivo sem
    nunca mostrar janela, mesmo depois de quatro minutos. O mesmo acontece
    com o instalador quando empacotado assim. Um onefile pequeno, de 8 MB,
    abre instantaneamente, entao o gatilho parece ser o volume gravado no
    temporario, provavelmente barrado pela protecao em tempo real.

    O modo esta aqui para quem quiser testar em outra maquina, e nao como
    caminho de distribuicao. Enquanto isso nao for resolvido, o que se
    entrega e a pasta, ou o instalador que a instala.
    """
    icone = gerar_icone()

    alvos = [RAIZ / "build"]
    alvos.append(RAIZ / "dist" / "MarkItDown.exe" if arquivo_unico
                 else RAIZ / "dist" / "MarkItDown")
    for alvo in alvos:
        if alvo.is_dir():
            shutil.rmtree(alvo)
        elif alvo.exists():
            alvo.unlink()

    comando = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--onefile" if arquivo_unico else "--onedir",
        "--name",
        "MarkItDown",
        "--collect-data",
        "magika",
        "--collect-binaries",
        "onnxruntime",
        "--collect-all",
        "numpy",
        "--icon",
        str(icone),
    ]
    if arquivo_unico:
        # O .spec do modo pasta e versionado. Mandar o do modo arquivo
        # unico para build/ evita sobrescrever um com o outro.
        comando += ["--specpath", str(RAIZ / "build")]
    comando.append(str(RAIZ / "main.py"))

    print("rodando:", " ".join(comando))
    codigo = subprocess.run(comando, cwd=RAIZ, check=False).returncode
    if codigo == 0:
        saida = (
            RAIZ / "dist" / "MarkItDown.exe" if arquivo_unico
            else RAIZ / "dist" / "MarkItDown"
        )
        print(f"pronto: {saida}")
    return codigo


if __name__ == "__main__":
    unico = "--onefile" in sys.argv or "--arquivo-unico" in sys.argv
    raise SystemExit(empacotar(arquivo_unico=unico))
