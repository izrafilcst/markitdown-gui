"""Nucleo do app: Python puro, sem nenhum import de Qt.

Essa separacao e a razao de o projeto ser testavel sem abrir janela.
Se algum dia aparecer um import de Qt aqui dentro, e bug. A regra e
verificada por tests/test_offline.py, que varre este pacote atras de
qualquer mencao ao pacote de Qt. Por isso o nome dele nao aparece escrito
nesta docstring: a varredura acusaria este proprio arquivo.
"""

from . import converter, discovery, formats, historico, naming

__all__ = ["converter", "discovery", "formats", "historico", "naming"]
