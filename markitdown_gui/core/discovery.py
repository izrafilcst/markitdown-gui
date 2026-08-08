"""Transforma o que foi solto na janela numa lista de arquivos convertiveis.

O usuario solta qualquer coisa: um arquivo, dez arquivos, uma pasta, uma
pasta cheia de subpastas, um atalho quebrado. Este modulo normaliza tudo
isso em duas listas: o que entra na fila e o que foi recusado e por que.

Nada aqui importa Qt. A UI passa uma lista de Path e recebe um resultado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import formats


@dataclass(frozen=True)
class Recusa:
    path: Path
    motivo: str


@dataclass
class Descoberta:
    aceitos: list[Path] = field(default_factory=list)
    recusados: list[Recusa] = field(default_factory=list)
    truncado: bool = False  # bateu no teto de MAX_ARQUIVOS

    @property
    def vazio(self) -> bool:
        return not self.aceitos


def _iter_arquivos(raiz: Path) -> Iterable[Path]:
    """Percorre uma pasta recursivamente, pulando o que nao interessa."""
    try:
        entradas = sorted(raiz.iterdir())
    except (PermissionError, OSError):
        return
    for entrada in entradas:
        nome = entrada.name
        # Pastas ocultas, de sistema e de ferramentas nunca contem
        # documentos que o usuario queira converter.
        if nome.startswith((".", "~$")):
            continue
        try:
            if entrada.is_dir():
                if nome in {"__pycache__", "node_modules", "$RECYCLE.BIN"}:
                    continue
                yield from _iter_arquivos(entrada)
            elif entrada.is_file():
                yield entrada
        except OSError:
            continue


def expandir(caminhos: Iterable[Path], ja_na_fila: set[Path] | None = None) -> Descoberta:
    """Expande pastas, filtra formatos e remove duplicatas.

    `ja_na_fila` evita que soltar o mesmo arquivo duas vezes crie duas
    linhas identicas na fila.
    """
    ja_na_fila = ja_na_fila or set()
    resultado = Descoberta()
    vistos: set[Path] = set()

    for bruto in caminhos:
        try:
            path = Path(bruto).resolve()
        except OSError:
            resultado.recusados.append(Recusa(Path(bruto), "Caminho invalido"))
            continue

        if not path.exists():
            resultado.recusados.append(
                Recusa(path, "O arquivo foi movido ou apagado")
            )
            continue

        candidatos = list(_iter_arquivos(path)) if path.is_dir() else [path]

        # Uma pasta sem nenhum documento convertivel merece aviso proprio.
        # Sem isso o usuario solta a pasta, nada acontece, e ele conclui
        # que o app esta quebrado.
        if path.is_dir() and not any(formats.is_supported(c) for c in candidatos):
            resultado.recusados.append(
                Recusa(path, "A pasta nao tem nenhum arquivo convertivel")
            )
            continue

        for arquivo in candidatos:
            if len(resultado.aceitos) >= formats.MAX_ARQUIVOS:
                resultado.truncado = True
                break

            if arquivo in vistos or arquivo in ja_na_fila:
                continue
            vistos.add(arquivo)

            if not formats.is_supported(arquivo):
                # Dentro de uma pasta, arquivo irrelevante e ruido: nao
                # vale poluir o aviso. Solto direto pelo usuario, e sinal
                # de intencao e merece explicacao.
                if not path.is_dir():
                    resultado.recusados.append(
                        Recusa(arquivo, formats.rejection_reason(arquivo))
                    )
                continue

            resultado.aceitos.append(arquivo)

        if resultado.truncado:
            break

    return resultado
