"""Ponto de entrada do MarkItDown."""
import sys

from PySide6.QtWidgets import QApplication

from markitdown_gui import APP_NAME, ORG_NAME
from markitdown_gui.ui import theme
from markitdown_gui.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    theme.aplicar(app)

    janela = MainWindow()
    janela.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
