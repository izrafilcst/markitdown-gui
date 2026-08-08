"""Persistencia das preferencias do usuario.

Camada fina sobre QSettings, que no Windows grava em HKCU e nao exige
arquivo de configuracao nem permissao de escrita em Program Files.

A regra que orienta este modulo: preferencia lida do disco e um palpite
sobre o passado, nao um fato sobre o presente. A pasta de destino lembrada
pode ter sido apagada, renomeada ou trocada por um arquivo desde a ultima
sessao. Por isso todo getter valida antes de devolver, e devolve None em
vez de estourar. Quem chama trata None como "pergunte de novo ao usuario",
que e sempre melhor do que abrir uma janela de erro na inicializacao.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

from .. import APP_NAME, ORG_NAME

CHAVE_DESTINO = "destino"
CHAVE_GEOMETRIA = "geometria"


class Preferencias:
    """Fino sobre QSettings. Chaves: destino, geometria."""

    def __init__(self) -> None:
        self._s = QSettings(ORG_NAME, APP_NAME)

    def destino(self) -> Path | None:
        """Pasta de destino lembrada, ou None se ela nao serve mais.

        Nao serve mais quer dizer: nunca foi gravada, foi apagada, ou o
        caminho existe mas virou arquivo.
        """
        bruto = self._s.value(CHAVE_DESTINO)
        if not bruto:
            return None
        try:
            caminho = Path(str(bruto))
            if caminho.is_dir():
                return caminho
        except OSError:
            # Caminho invalido para o sistema de arquivos, por exemplo uma
            # unidade de rede que sumiu. Vale o mesmo que nao ter destino.
            return None
        return None

    def definir_destino(self, pasta: Path) -> None:
        self._s.setValue(CHAVE_DESTINO, str(pasta))
        self._s.sync()

    def geometria(self) -> QByteArray | None:
        """Geometria da janela, opaca de proposito: so o Qt a interpreta."""
        bruto = self._s.value(CHAVE_GEOMETRIA)
        if bruto is None:
            return None
        if isinstance(bruto, QByteArray):
            return bruto if not bruto.isEmpty() else None
        if isinstance(bruto, (bytes, bytearray)):
            return QByteArray(bytes(bruto)) if bruto else None
        return None

    def definir_geometria(self, dados: QByteArray) -> None:
        self._s.setValue(CHAVE_GEOMETRIA, dados)
        self._s.sync()

    def limpar(self) -> None:
        """Apaga tudo. Existe para os testes conseguirem partir do zero.

        Nao esta no contrato 4.6, mas tambem nao muda nenhuma assinatura de
        la: e adicao, nao alteracao.
        """
        self._s.clear()
        self._s.sync()
