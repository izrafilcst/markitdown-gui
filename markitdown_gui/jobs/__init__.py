"""Orquestracao da fila de conversao.

Esta camada conhece Qt e conhece o core. O core nao conhece nenhuma das
duas coisas, e a interface nao conhece o core diretamente.

O pacote se chama `jobs` e nao `queue` de proposito: `queue` e um modulo
da biblioteca padrao, e sombrear ele quebra o empacotamento.

Os submodulos sao importados sob demanda, e nao aqui, para que importar
`markitdown_gui.jobs.models` num teste nao arraste Qt junto.
"""

__all__ = ["models", "worker", "controller"]
