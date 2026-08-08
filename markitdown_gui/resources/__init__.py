"""Recursos embarcados no pacote.

Nada de binario grande aqui. Os icones sao SVG escrito como string em
`markitdown_gui/ui/icons.py`, justamente para que o PyInstaller nao precise
de nenhuma regra extra de coleta de dados.

A pasta `fonts/` e opcional: se estiver vazia, `theme.carregar_fontes` nao
faz nada e a cadeia de fallback de `theme.FONT` resolve para a fonte do
sistema.
"""
