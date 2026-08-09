"""Ponto de entrada do MarkItDown."""
import sys

from PySide6.QtWidgets import QApplication

from markitdown_gui import APP_NAME, ORG_NAME
from markitdown_gui.ui import icons, theme
from markitdown_gui.ui.main_window import MainWindow


def _identificar_para_a_barra_de_tarefas() -> None:
    """Faz o Windows agrupar as janelas sob o icone do app.

    Sem um AppUserModelID proprio, o Windows agrupa o programa sob o
    icone do interpretador Python quando ele roda a partir do codigo,
    e o icone da janela nao chega a barra de tarefas. Nao faz nada em
    outros sistemas nem no executavel empacotado, onde o proprio .exe
    ja resolve isso.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{ORG_NAME}.{APP_NAME}"
        )
    except Exception:
        # Cosmetico: falhar aqui nao pode impedir o app de abrir.
        pass


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    # Sem argumento, aplicar segue o tema claro ou escuro do Windows.
    theme.aplicar(app)
    theme.seguir_o_sistema(app)

    _identificar_para_a_barra_de_tarefas()
    app.setWindowIcon(icons.icone_do_app())

    janela = MainWindow()
    janela.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
