"""Logica do instalador, sem interface e sem Qt.

Separado do resto pelo mesmo motivo que `markitdown_gui/core` e separado da
interface: instalar mexe em PATH, em registro e em pastas do usuario, e
essas operacoes precisam ser testaveis sem abrir janela e sem sujar a
maquina de quem roda os testes.

Nada aqui pede privilegio de administrador. A instalacao vai para a pasta
do usuario, que e o padrao moderno no Windows e evita a caixa de elevacao
que assusta usuario nao tecnico. O preco e que o programa fica instalado
por usuario, e nao para a maquina inteira, o que para este app e o que
faz sentido.
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

APP = "MarkItDown"
EXECUTAVEL = f"{APP}.exe"
CHAVE_DESINSTALACAO = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP}"

# Arquivos sem os quais o programa nao roda. Conferir a existencia deles
# depois de extrair e o que transforma "copiei os bytes" em "instalei".
# Os dois ultimos ja quebraram o empacotamento neste projeto, entao estao
# aqui por experiencia, nao por precaucao generica.
ESSENCIAIS = (
    EXECUTAVEL,
    "_internal/base_library.zip",
    "_internal/magika/models/standard_v3_3/model.onnx",
    "_internal/onnxruntime/capi/onnxruntime.dll",
)


@dataclass(frozen=True)
class Verificacao:
    """Resultado da conferencia de uma instalacao."""

    completa: bool
    faltando: tuple[str, ...]
    arquivos: int
    bytes_totais: int

    @property
    def resumo(self) -> str:
        if self.completa:
            mb = self.bytes_totais / (1024 * 1024)
            return f"{self.arquivos} arquivos, {mb:.0f} MB, tudo no lugar"
        return "Faltando: " + ", ".join(self.faltando)


def destino_padrao(base: Path | None = None) -> Path:
    """Onde instalar sem precisar de administrador.

    `%LOCALAPPDATA%\\Programs` e o lugar que o proprio Windows usa para
    programas por usuario. Instalar em Arquivos de Programas exigiria
    elevacao, e o usuario deste app nao deveria ter que responder a uma
    caixa de permissao para converter um PDF.
    """
    if base is None:
        bruto = os.environ.get("LOCALAPPDATA")
        base = Path(bruto) if bruto else Path.home() / "AppData" / "Local"
    return Path(base) / "Programs" / APP


def verificar(destino: Path) -> Verificacao:
    """Confere se a instalacao em `destino` esta completa e utilizavel."""
    faltando = [alvo for alvo in ESSENCIAIS if not existe(destino / alvo)]
    arquivos = 0
    tamanho = 0
    raiz = caminho_longo(destino)
    if os.path.isdir(raiz):
        # os.walk e nao Path.rglob: o rglob volta a montar Path comuns, que
        # perdem o prefixo de caminho longo e tornam a contagem incompleta
        # justamente nas pastas mais fundas.
        for pasta, _subpastas, nomes in os.walk(raiz):
            for nome in nomes:
                arquivos += 1
                try:
                    tamanho += os.path.getsize(os.path.join(pasta, nome))
                except OSError:
                    pass
    return Verificacao(
        completa=not faltando and arquivos > 0,
        faltando=tuple(faltando),
        arquivos=arquivos,
        bytes_totais=tamanho,
    )


def caminho_longo(destino: Path | str) -> str:
    """Forma do caminho que escapa do limite de 260 caracteres do Windows.

    Isto nao e teoria. A carga deste app traz o `lxml`, cujo pacote tem
    caminhos como
    `_internal/lxml/isoschematron/resources/xsl/iso-schematron-xslt1/...`.
    Somados a uma pasta de destino um pouco funda, eles passam de 260, e a
    extracao morre no meio com FileNotFoundError, deixando o programa
    instalado pela metade. O prefixo `\\\\?\\` faz o Windows usar a API
    longa e o problema desaparece.
    """
    bruto = str(destino)
    if os.name != "nt":
        return bruto
    if bruto.startswith("\\\\?\\"):
        return bruto
    absoluto = os.path.abspath(bruto)
    if absoluto.startswith("\\\\"):          # compartilhamento de rede
        return "\\\\?\\UNC" + absoluto[1:]
    return "\\\\?\\" + absoluto


def criar_pastas(destino: Path) -> None:
    """mkdir que aguenta caminho longo."""
    os.makedirs(caminho_longo(destino), exist_ok=True)


def existe(alvo: Path) -> bool:
    """exists() que aguenta caminho longo."""
    return os.path.exists(caminho_longo(alvo))


def gravar_bytes(alvo: Path, dados: bytes) -> None:
    criar_pastas(alvo.parent)
    with open(caminho_longo(alvo), "wb") as saida:
        saida.write(dados)


def extrair(pacote: Path, destino: Path, progresso=None) -> int:
    """Extrai o pacote em `destino`, avisando o progresso pelo caminho.

    `progresso` recebe (feitos, total) e existe para a barra da interface.
    Devolve quantos arquivos foram gravados.
    """
    criar_pastas(destino)
    alvo = caminho_longo(destino)
    with zipfile.ZipFile(pacote) as z:
        membros = z.infolist()
        total = len(membros)
        for indice, membro in enumerate(membros, start=1):
            z.extract(membro, alvo)
            if progresso is not None:
                progresso(indice, total)
    return total


def entradas_do_path(valor: str) -> list[str]:
    """Quebra um PATH em partes, sem deixar vazio nem espaco solto."""
    return [parte.strip() for parte in valor.split(os.pathsep) if parte.strip()]


def _mesmo_caminho(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(
        os.path.normpath(b)
    )


def path_com(valor: str, pasta: Path) -> str:
    """Devolve o PATH com `pasta` presente, sem duplicar.

    Comparar por texto puro nao serve: `C:\\App` e `C:\\App\\` sao a mesma
    pasta e o Windows nao diferencia maiuscula de minuscula. Sem
    normalizar, cada reinstalacao acrescentaria mais uma copia, e um PATH
    inchado e um estrago silencioso que sobrevive a desinstalacao.
    """
    partes = entradas_do_path(valor)
    alvo = str(pasta)
    if any(_mesmo_caminho(parte, alvo) for parte in partes):
        return os.pathsep.join(partes)
    return os.pathsep.join([*partes, alvo])


def path_sem(valor: str, pasta: Path) -> str:
    """Devolve o PATH sem nenhuma referencia a `pasta`.

    Usado na desinstalacao: deixar lixo no PATH depois de remover o
    programa e uma das coisas que mais irritam em instalador ruim.
    """
    alvo = str(pasta)
    return os.pathsep.join(
        parte for parte in entradas_do_path(valor)
        if not _mesmo_caminho(parte, alvo)
    )


def destino_seguro(destino: Path) -> bool:
    """Recusa destinos que apagariam algo que nao e nosso.

    A desinstalacao apaga a pasta inteira, entao apontar a instalacao para
    a raiz de um disco, para a pasta pessoal ou para uma pasta ja cheia de
    outra coisa seria destrutivo. Melhor recusar na hora de instalar do
    que descobrir na hora de desinstalar.
    """
    destino = Path(destino)
    if not destino.is_absolute():
        return False
    if destino.parent == destino:            # raiz de disco
        return False
    proibidos = {Path.home(), Path.home() / "Desktop", Path.home() / "Documents"}
    if destino in proibidos:
        return False
    if destino.exists():
        if not destino.is_dir():
            return False
        # Pasta existente so serve se estiver vazia ou se ja for uma
        # instalacao nossa, caso de reinstalacao ou atualizacao.
        conteudo = list(destino.iterdir())
        if conteudo and not (destino / EXECUTAVEL).exists():
            return False
    return True
