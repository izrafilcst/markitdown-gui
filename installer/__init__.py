"""Instalador do MarkItDown.

Tres camadas, pela mesma razao que o app tem tres:

`nucleo.py`   logica pura, sem interface e sem Windows. E o que tem teste.
`windows.py`  as chamadas que mexem no sistema de verdade: PATH, atalhos,
              registro. Fina de proposito, porque nao da para testar sem
              estragar a maquina de quem roda a suite.
`setup_app.py` o assistente em tkinter, que so desenha e chama os outros.

O instalador nao importa nada de `markitdown_gui`: ele precisa rodar antes
de o app existir na maquina.
"""

__all__ = ["nucleo", "windows", "setup_app"]
