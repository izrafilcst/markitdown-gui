"""A unidade de trabalho que roda fora da thread da interface.

Um QRunnable nao pode emitir sinais (nao e QObject), entao o padrao e
carregar um objeto de sinais junto. As conexoes cruzam de thread com
QueuedConnection automaticamente, que e o que mantem a UI viva enquanto
quatro PDFs sao convertidos ao mesmo tempo.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..core import converter


class SinaisDoWorker(QObject):
    concluiu = Signal(str, str, int)   # item_id, caminho_destino, caracteres
    falhou = Signal(str, str, str)     # item_id, mensagem, detalhe


class ConversionWorker(QRunnable):
    def __init__(self, item_id: str, origem: Path, destino: Path):
        super().__init__()
        self.item_id = item_id
        self.origem = origem
        self.destino = destino
        self.sinais = SinaisDoWorker()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            resultado = converter.converter(self.origem)
            converter.gravar(resultado.markdown, self.destino)
        except converter.ErroDeConversao as exc:
            self.sinais.falhou.emit(self.item_id, exc.mensagem, exc.detalhe)
        except Exception as exc:  # nunca deixar excecao escapar de um QRunnable
            self.sinais.falhou.emit(
                self.item_id,
                "Erro inesperado ao converter",
                f"{type(exc).__name__}: {exc}",
            )
        else:
            self.sinais.concluiu.emit(
                self.item_id, str(self.destino), resultado.caracteres
            )
