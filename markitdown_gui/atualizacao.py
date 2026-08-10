"""Verificacao de atualizacao. O UNICO lugar do pacote que toca a rede.

Vale ser explicito sobre o que este arquivo muda na promessa do produto.

O app promete que **seus documentos nunca saem da maquina**, e isso
continua valendo sem excecao: `core/` e `jobs/`, que sao por onde o
documento passa, seguem provados sem rede por
`tests/test_offline.py::test_o_caminho_de_conversao_continua_sem_rede`.

O que este modulo acrescenta e um segundo caminho, que nao toca em
documento nenhum: uma consulta de versao ao GitHub. Ela e:

- **pedida pelo usuario**, nunca automatica. O app nao telefona para casa
  ao abrir;
- **um GET simples**, sem corpo, sem identificador, sem telemetria. O
  servidor descobre que alguem perguntou a versao, e nada mais;
- **opcional**. Sem internet, o app funciona igual e a verificacao
  informa que nao deu.

Havia a alternativa de esconder este codigo num pacote fora da varredura
estatica, o que manteria o teste verde. Seria contornar o proprio teste, e
a promessa ficaria falsa enquanto parecia verdadeira. Preferimos estreitar
a promessa e travar a versao nova dela por teste.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPOSITORIO = "izrafilcst/markitdown-gui"
URL_DA_ULTIMA_VERSAO = f"https://api.github.com/repos/{REPOSITORIO}/releases/latest"
NOME_DO_INSTALADOR = "MarkItDown-Setup.exe"

# De onde e aceitavel baixar um executavel. A URL chega de uma resposta de
# rede, e baixar e executar um .exe de origem arbitraria seria o pior
# desfecho possivel deste recurso.
HOSTS_CONFIAVEIS = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)

_NUMERO = re.compile(r"^\d+(\.\d+)*$")


@dataclass(frozen=True)
class Resultado:
    """O que a consulta descobriu."""

    disponivel: bool = False
    versao: str = ""
    instalador: str = ""
    pagina: str = ""
    notas: str = ""
    erro: str = ""
    tamanho: int = field(default=0)

    @property
    def tamanho_legivel(self) -> str:
        if self.tamanho <= 0:
            return ""
        return f"{self.tamanho / 1024 / 1024:.0f} MB"


def _partes(versao: str) -> tuple[int, ...] | None:
    """Quebra "v1.2.3" em (1, 2, 3). Devolve None se nao for versao."""
    limpa = versao.strip().lstrip("vV")
    if not limpa or not _NUMERO.match(limpa):
        return None
    return tuple(int(p) for p in limpa.split("."))


def ha_versao_nova(instalada: str, publicada: str) -> bool:
    """Compara numero a numero, e nao como texto.

    Comparar texto diria que "1.9.0" e maior que "1.10.0", porque "9" vem
    depois de "1". Erro classico, e que so aparece na decima versao menor.
    """
    a, b = _partes(instalada), _partes(publicada)
    if a is None or b is None:
        return False
    tamanho = max(len(a), len(b))
    a = a + (0,) * (tamanho - len(a))
    b = b + (0,) * (tamanho - len(b))
    return b > a


def origem_confiavel(url: str) -> bool:
    """Aceita apenas HTTPS vindo dos dominios de release do GitHub.

    A comparacao e por componente de host, e nao por "contem": um dominio
    como `github.com.malicioso.io` passaria numa checagem ingenua.
    """
    from urllib.parse import urlparse

    partes = urlparse(url)
    if partes.scheme != "https":
        return False
    host = (partes.hostname or "").lower()
    return any(host == confiavel for confiavel in HOSTS_CONFIAVEIS)


def _buscar(url: str, tempo_limite: int = 10) -> bytes:
    """Faz o GET. Isolado numa funcao para o teste poder substituir."""
    pedido = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MarkItDown",
        },
    )
    with urllib.request.urlopen(pedido, timeout=tempo_limite) as resposta:
        return resposta.read()


def verificar(versao_instalada: str, tempo_limite: int = 10) -> Resultado:
    """Pergunta ao GitHub qual e a ultima versao publicada.

    Nunca levanta excecao: qualquer problema vira `erro` em portugues, com
    a mensagem escrita para quem nao e tecnico.
    """
    import json

    try:
        bruto = _buscar(URL_DA_ULTIMA_VERSAO, tempo_limite=tempo_limite)
    except (urllib.error.URLError, OSError, ValueError):
        return Resultado(
            erro="Nao foi possivel falar com o servidor. "
            "Verifique sua conexao com a internet e tente de novo."
        )

    try:
        dados = json.loads(bruto)
        tag = str(dados.get("tag_name", ""))
        pagina = str(dados.get("html_url", ""))
        notas = str(dados.get("body", "") or "")
        arquivos = dados.get("assets") or []
    except (ValueError, TypeError, AttributeError):
        return Resultado(erro="A resposta do servidor veio em um formato inesperado.")

    versao = tag.lstrip("vV")
    instalador = ""
    tamanho = 0
    for arquivo in arquivos:
        if str(arquivo.get("name", "")) == NOME_DO_INSTALADOR:
            instalador = str(arquivo.get("browser_download_url", ""))
            tamanho = int(arquivo.get("size", 0) or 0)
            break

    if not instalador:
        return Resultado(
            versao=versao,
            pagina=pagina,
            erro="A versao publicada nao traz instalador para Windows.",
        )

    return Resultado(
        disponivel=ha_versao_nova(versao_instalada, versao),
        versao=versao,
        instalador=instalador,
        pagina=pagina,
        notas=notas,
        tamanho=tamanho,
    )


def baixar_instalador(
    url: str, pasta: Path, tempo_limite: int = 60, progresso=None
) -> Path | None:
    """Baixa o instalador. Devolve o caminho, ou None se nao deu.

    A origem e conferida ANTES de gravar qualquer byte.
    """
    if not origem_confiavel(url):
        return None
    try:
        conteudo = _buscar(url, tempo_limite=tempo_limite)
    except (urllib.error.URLError, OSError, ValueError):
        return None

    try:
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / NOME_DO_INSTALADOR
        destino.write_bytes(conteudo)
    except OSError:
        return None

    if progresso is not None:
        progresso(len(conteudo), len(conteudo))
    return destino
