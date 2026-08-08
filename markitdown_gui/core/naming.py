"""Regra de nome do arquivo de saida.

livro_cavalos.pdf  ->  livro_cavalos_convertido.md

Se o nome ja existir, entra sufixo numerico no estilo do Windows:
livro_cavalos_convertido (2).md

Duas fontes de colisao precisam ser consideradas juntas, e esquecer a
segunda e o bug classico aqui:
  1. arquivos que ja estao no disco
  2. nomes ja prometidos a outros itens da mesma fila, que ainda nao
     foram gravados

Por isso resolve_output_path recebe um conjunto de nomes ja reservados.
"""

from __future__ import annotations

import re
from pathlib import Path

SUFIXO = "_convertido"

# Caracteres proibidos em nome de arquivo no Windows. Um .zip pode conter
# entradas com esses caracteres, e um arquivo baixado da web tambem.
_INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Nomes reservados pelo Windows. Criar CON.md falha de forma obscura.
_RESERVADOS = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_stem(stem: str) -> str:
    """Deixa o nome base seguro para virar arquivo no Windows."""
    limpo = _INVALIDOS.sub("_", stem).strip().rstrip(".")
    if not limpo:
        limpo = "sem_nome"
    if limpo.upper() in _RESERVADOS:
        limpo = f"{limpo}_"
    # O Windows corta em 255 por componente. Deixamos folga para o sufixo,
    # a extensao e um eventual " (99)".
    return limpo[:180]


def output_filename(source: Path) -> str:
    """Nome de saida ideal, antes de resolver colisao."""
    return f"{sanitize_stem(source.stem)}{SUFIXO}.md"


def resolve_output_path(
    source: Path,
    dest_dir: Path,
    reservados: set[Path] | None = None,
) -> Path:
    """Caminho final de gravacao, ja livre de colisao.

    Nao toca no disco alem de checar existencia. Quem grava e o worker.
    """
    reservados = reservados if reservados is not None else set()
    base = f"{sanitize_stem(source.stem)}{SUFIXO}"

    candidato = dest_dir / f"{base}.md"
    contador = 2
    while candidato.exists() or candidato in reservados:
        candidato = dest_dir / f"{base} ({contador}).md"
        contador += 1
        if contador > 9999:  # cinto de seguranca, nunca deve acontecer
            raise RuntimeError(
                f"Nao foi possivel achar um nome livre para {source.name}"
            )
    return candidato
