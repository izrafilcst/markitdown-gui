"""O que e um item da fila.

Sem Qt aqui tambem: e uma estrutura de dados simples, para que a logica
de estado possa ser testada sem instanciar aplicacao grafica.

O nome do pacote e `jobs` e nao `queue` de proposito: `queue` e um modulo
da biblioteca padrao do Python, e sombrear ele causa falhas obscuras
justamente durante o empacotamento com PyInstaller.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Estado(str, Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    FALHOU = "falhou"
    CANCELADO = "cancelado"

    @property
    def rotulo(self) -> str:
        return {
            Estado.PENDENTE: "Aguardando",
            Estado.PROCESSANDO: "Convertendo",
            Estado.CONCLUIDO: "Concluido",
            Estado.FALHOU: "Falhou",
            Estado.CANCELADO: "Cancelado",
        }[self]

    @property
    def terminal(self) -> bool:
        return self in (Estado.CONCLUIDO, Estado.FALHOU, Estado.CANCELADO)


_contador = itertools.count(1)


@dataclass
class Item:
    origem: Path
    id: str = field(default_factory=lambda: f"item-{next(_contador)}")
    estado: Estado = Estado.PENDENTE
    mensagem: str = ""
    detalhe: str = ""
    destino: Path | None = None
    caracteres: int = 0

    @property
    def nome(self) -> str:
        return self.origem.name

    @property
    def pode_remover(self) -> bool:
        # Nao ha como matar uma thread em Python. Em vez de fingir que da,
        # o botao de remover simplesmente nao aparece durante a conversao.
        return self.estado is not Estado.PROCESSANDO

    @property
    def pode_repetir(self) -> bool:
        return self.estado in (Estado.FALHOU, Estado.CANCELADO)

    def reiniciar(self) -> None:
        self.estado = Estado.PENDENTE
        self.mensagem = ""
        self.detalhe = ""
        self.destino = None
        self.caracteres = 0
