"""Historico local das conversoes.

Guarda o que foi convertido, quando, para onde e com que resultado. Fica
em SQLite, que vem na biblioteca padrao e nao adiciona dependencia nem
arquivo de configuracao para o usuario cuidar.

Tres regras governam este modulo:

1. **Nada sai da maquina.** O historico e local, como o resto do app. Ele
   guarda nome de arquivo, que e informacao do usuario, e por isso existe
   `limpar()`: quem quiser apagar tudo consegue, por completo.
2. **Historico nunca derruba conversao.** Guardar o registro e
   conveniencia; converter e o produto. Qualquer falha de banco vira
   silencio aqui dentro, e a fila segue. O contrario, perder uma conversao
   por causa de um log, seria trocar o essencial pelo acessorio.
3. **Nao cresce sem limite.** Ha um teto de registros, e o mais velho sai
   quando entra um novo. Encher o disco de alguem em silencio nao e
   aceitavel.

Sem Qt aqui, como todo o resto de `core/`.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAX_REGISTROS = 500

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS conversoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    quando     TEXT    NOT NULL,
    origem     TEXT    NOT NULL,
    destino    TEXT    NOT NULL,
    caracteres INTEGER NOT NULL DEFAULT 0,
    sucesso    INTEGER NOT NULL DEFAULT 1,
    mensagem   TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_quando ON conversoes(quando DESC);
"""


def caminho_padrao() -> Path:
    """Onde o historico mora, na pasta de dados do usuario."""
    bruto = os.environ.get("LOCALAPPDATA")
    base = Path(bruto) if bruto else Path.home() / "AppData" / "Local"
    return base / "MarkItDown" / "historico.db"


@dataclass(frozen=True)
class Registro:
    """Uma conversao que aconteceu."""

    id: int
    quando: datetime
    origem: Path
    destino: Path
    caracteres: int
    sucesso: bool
    mensagem: str

    def quando_legivel(self) -> str:
        """Data em portugues, relativa quando isso ajuda a entender.

        "hoje as 14:32" diz mais do que "09/08/2026 14:32" para quem
        acabou de converter, e a data cheia continua aparecendo assim que
        deixa de ser obvia.
        """
        agora = datetime.now()
        se_hoje = self.quando.date() == agora.date()
        if se_hoje:
            return f"hoje as {self.quando:%H:%M}"
        dias = (agora.date() - self.quando.date()).days
        if dias == 1:
            return f"ontem as {self.quando:%H:%M}"
        return f"{self.quando:%d/%m/%Y as %H:%M}"

    def tamanho_legivel(self) -> str:
        """Quantidade de texto extraido, em unidade que o usuario entende."""
        if self.caracteres <= 0:
            return "sem texto"
        if self.caracteres < 1000:
            return f"{self.caracteres} caracteres"
        if self.caracteres < 1_000_000:
            return f"{self.caracteres / 1000:.0f} mil caracteres"
        return f"{self.caracteres / 1_000_000:.1f} milhoes de caracteres"


class Historico:
    """Livro local das conversoes."""

    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = Path(caminho) if caminho is not None else caminho_padrao()
        self._preparar()

    # ------------------------------------------------------------ apoio

    def _conectar(self) -> sqlite3.Connection:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conexao = sqlite3.connect(str(self.caminho))
        conexao.row_factory = sqlite3.Row
        return conexao

    def _preparar(self) -> None:
        try:
            with self._conectar() as conexao:
                conexao.executescript(_ESQUEMA)
        except (sqlite3.Error, OSError):
            # Sem banco, o app continua convertendo. Ver regra 2.
            pass

    # --------------------------------------------------------- comandos

    def registrar(
        self,
        origem: Path,
        destino: Path,
        caracteres: int = 0,
        sucesso: bool = True,
        mensagem: str = "",
    ) -> int | None:
        """Guarda uma conversao. Devolve o id, ou None se nao deu.

        Devolver None em vez de levantar e deliberado: quem chama e o
        controller, no meio da fila, e uma excecao aqui interromperia a
        conversao seguinte por causa de um registro que e so historico.
        """
        try:
            with self._conectar() as conexao:
                cursor = conexao.execute(
                    "INSERT INTO conversoes "
                    "(quando, origem, destino, caracteres, sucesso, mensagem) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        str(origem),
                        str(destino),
                        int(caracteres),
                        1 if sucesso else 0,
                        mensagem,
                    ),
                )
                novo = cursor.lastrowid
                self._podar(conexao)
                return novo
        except (sqlite3.Error, OSError, ValueError):
            return None

    def _podar(self, conexao: sqlite3.Connection) -> None:
        """Descarta os mais antigos alem do teto."""
        conexao.execute(
            "DELETE FROM conversoes WHERE id NOT IN ("
            "  SELECT id FROM conversoes ORDER BY id DESC LIMIT ?"
            ")",
            (MAX_REGISTROS,),
        )

    def recentes(self, limite: int = 100) -> list[Registro]:
        """Conversoes mais recentes primeiro. Lista vazia se algo falhar."""
        try:
            with self._conectar() as conexao:
                linhas = conexao.execute(
                    "SELECT id, quando, origem, destino, caracteres, sucesso, "
                    "mensagem FROM conversoes ORDER BY id DESC LIMIT ?",
                    (int(limite),),
                ).fetchall()
        except (sqlite3.Error, OSError, ValueError):
            return []

        registros = []
        for linha in linhas:
            try:
                quando = datetime.fromisoformat(linha["quando"])
            except (TypeError, ValueError):
                continue
            registros.append(
                Registro(
                    id=linha["id"],
                    quando=quando,
                    origem=Path(linha["origem"]),
                    destino=Path(linha["destino"]),
                    caracteres=linha["caracteres"],
                    sucesso=bool(linha["sucesso"]),
                    mensagem=linha["mensagem"] or "",
                )
            )
        return registros

    def remover(self, registro_id: int) -> None:
        try:
            with self._conectar() as conexao:
                conexao.execute(
                    "DELETE FROM conversoes WHERE id = ?", (int(registro_id),)
                )
        except (sqlite3.Error, OSError, ValueError):
            pass

    def limpar(self) -> None:
        """Apaga o historico inteiro.

        Existe porque o app guarda nome de arquivo do usuario, e quem
        guarda dado de alguem precisa oferecer o botao de apagar.
        """
        try:
            with self._conectar() as conexao:
                conexao.execute("DELETE FROM conversoes")
        except (sqlite3.Error, OSError):
            pass

    def quantidade(self) -> int:
        try:
            with self._conectar() as conexao:
                (total,) = conexao.execute(
                    "SELECT COUNT(*) FROM conversoes"
                ).fetchone()
                return int(total)
        except (sqlite3.Error, OSError, TypeError):
            return 0
