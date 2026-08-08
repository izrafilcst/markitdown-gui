"""Nucleo do app: Python puro, sem nenhum import de Qt.

Essa separacao e a razao de o projeto ser testavel sem abrir janela.
Se algum dia aparecer um `from PySide6 import ...` aqui dentro, e bug.
"""

from . import converter, discovery, formats, naming

__all__ = ["converter", "discovery", "formats", "naming"]
