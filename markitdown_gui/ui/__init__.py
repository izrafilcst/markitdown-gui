"""Camada de apresentacao: so desenha e conecta sinais.

Nenhuma regra de negocio mora aqui. Nenhum valor de cor literal mora aqui
fora de `theme.py`, que e a unica fonte dos tokens de design.

Os submodulos sao importados sob demanda para manter o custo de import
baixo e para que os modulos possam ser criados em paralelo.
"""

__all__ = [
    "theme",
    "icons",
    "prefs",
    "drop_zone",
    "destino_bar",
    "queue_row",
    "queue_view",
    "main_window",
]
