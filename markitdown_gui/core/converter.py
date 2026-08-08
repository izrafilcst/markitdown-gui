"""Camada fina sobre a biblioteca markitdown da Microsoft.

Este arquivo e proposital e deliberadamente pequeno. O MarkItDown e uma
dependencia, nunca codigo copiado ou reescrito: se a Microsoft lancar uma
versao nova, sobe-se a versao no requirements.txt e nada aqui muda.

O que este modulo adiciona, e que a biblioteca nao da:
  1. uma instancia por thread, porque a fila converte em paralelo
  2. garantia de que nada sai da maquina
  3. traducao de excecao tecnica para frase que um humano entende
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from markitdown import MarkItDown

# Os nomes das excecoes variam entre versoes do markitdown. Importar de
# forma defensiva evita que uma atualizacao da biblioteca quebre o app
# com ImportError na inicializacao.
try:  # pragma: no cover - depende da versao instalada
    from markitdown import FileConversionException, UnsupportedFormatException
except ImportError:  # pragma: no cover
    class FileConversionException(Exception): ...
    class UnsupportedFormatException(Exception): ...

try:  # pragma: no cover
    from markitdown import MissingDependencyException
except ImportError:  # pragma: no cover
    class MissingDependencyException(Exception): ...


class ErroDeConversao(Exception):
    """Falha ja traduzida para o usuario final.

    `mensagem` vai para a linha da fila. `detalhe` fica escondido atras do
    "ver detalhes", para quando alguem precisar depurar de verdade.
    """

    def __init__(self, mensagem: str, detalhe: str = ""):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhe = detalhe


@dataclass(frozen=True)
class Resultado:
    markdown: str
    caracteres: int


_local = threading.local()


def _engine() -> MarkItDown:
    """Uma instancia de MarkItDown por thread.

    Compartilhar uma instancia entre threads nao e garantido pela
    biblioteca, e criar uma por arquivo desperdicaria o carregamento do
    modelo de deteccao de tipo (magika). Uma por thread resolve os dois.

    enable_plugins=False e uma trava de privacidade, nao uma otimizacao:
    um plugin de terceiro instalado no sistema poderia fazer chamada de
    rede, e o app promete funcionar 100% offline.
    """
    engine = getattr(_local, "engine", None)
    if engine is None:
        engine = MarkItDown(enable_plugins=False)
        _local.engine = engine
    return engine


def _texto(resultado) -> str:
    """Le o markdown do resultado, tolerando mudanca de nome do atributo."""
    for attr in ("markdown", "text_content"):
        valor = getattr(resultado, attr, None)
        if isinstance(valor, str):
            return valor
    raise ErroDeConversao(
        "Erro inesperado ao ler o resultado",
        f"O objeto devolvido pelo markitdown nao tem markdown nem "
        f"text_content: {type(resultado)!r}",
    )


def converter(origem: Path) -> Resultado:
    """Converte um arquivo para Markdown. Nao grava nada em disco.

    Levanta ErroDeConversao com mensagem pronta para exibir.
    """
    try:
        bruto = _engine().convert(str(origem))
    except UnsupportedFormatException as exc:
        raise ErroDeConversao(
            "Este tipo de arquivo nao e suportado", str(exc)
        ) from exc
    except MissingDependencyException as exc:
        raise ErroDeConversao(
            "Falta um componente para ler este formato", str(exc)
        ) from exc
    except FileConversionException as exc:
        raise ErroDeConversao(
            "Nao foi possivel ler o arquivo. Ele pode estar corrompido "
            "ou protegido por senha",
            str(exc),
        ) from exc
    except FileNotFoundError as exc:
        raise ErroDeConversao("O arquivo foi movido ou apagado", str(exc)) from exc
    except PermissionError as exc:
        raise ErroDeConversao(
            "Sem permissao para abrir este arquivo", str(exc)
        ) from exc
    except MemoryError as exc:
        raise ErroDeConversao(
            "O arquivo e grande demais para a memoria disponivel", str(exc)
        ) from exc
    except Exception as exc:  # rede de seguranca: a fila nunca para
        raise ErroDeConversao(
            "Erro inesperado ao converter",
            f"{type(exc).__name__}: {exc}",
        ) from exc

    texto = _texto(bruto)
    return Resultado(markdown=texto, caracteres=len(texto))


def gravar(markdown: str, destino: Path) -> None:
    """Grava o Markdown em UTF-8, traduzindo falhas de escrita."""
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(markdown, encoding="utf-8", newline="\n")
    except PermissionError as exc:
        raise ErroDeConversao(
            "Sem permissao para salvar na pasta de destino", str(exc)
        ) from exc
    except OSError as exc:
        raise ErroDeConversao(
            "Nao foi possivel salvar o arquivo convertido",
            f"{type(exc).__name__}: {exc}",
        ) from exc
