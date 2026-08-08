import os
import sys
from pathlib import Path

import pytest

# Widgets precisam de plataforma offscreen para rodar sem monitor.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


@pytest.fixture
def pasta(tmp_path):
    """Pasta temporaria isolada por teste."""
    return tmp_path


@pytest.fixture(scope="session")
def qapp():
    """QApplication unica para a sessao inteira de testes de widget."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
