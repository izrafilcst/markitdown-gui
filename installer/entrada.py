"""Ponto de entrada do instalador.

Existe porque `setup_app.py` usa imports relativos, que nao funcionam
quando um arquivo e executado como programa principal. Este modulo garante
que a raiz do projeto esteja no caminho de import e chama o assistente,
tanto rodando do codigo quanto congelado pelo PyInstaller.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from installer.setup_app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
