"""Quais extensoes o app aceita, e por que recusa as demais.

Este modulo e a fonte unica de verdade sobre formatos. A UI le daqui para
montar a lista que aparece na zona de arraste, e o discovery le daqui para
decidir o que entra na fila. Nao existe segunda lista em lugar nenhum.

A regra que governa tudo aqui: so entra formato que o MarkItDown converte
sem tocar na rede. Ver docs/design.md, decisao 4.
"""

from __future__ import annotations

from pathlib import Path

# Formatos aceitos, agrupados como o usuario pensa neles, nao como o
# MarkItDown os organiza internamente. A ordem importa: e a ordem em que
# aparecem na zona de arraste.
SUPPORTED: dict[str, tuple[str, ...]] = {
    "PDF": (".pdf",),
    "Word": (".docx",),
    "Excel": (".xlsx", ".xls"),
    "PowerPoint": (".pptx",),
    "E-mail": (".msg",),
    "Web": (".html", ".htm"),
    "Dados": (".csv", ".json", ".xml"),
    "Livro": (".epub",),
    "Texto": (".txt", ".md", ".markdown"),
    "Pacote": (".zip",),
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    ext for grupo in SUPPORTED.values() for ext in grupo
)

# Formatos que o MarkItDown ate reconhece, mas que recusamos de proposito.
# Cada um traz o motivo em linguagem de usuario, porque recusar em silencio
# e pior do que nao aceitar: o usuario fica sem saber se o app quebrou.
REJECTED: dict[str, str] = {
    **{
        ext: "Imagens so gerariam um arquivo vazio, porque a leitura de "
        "texto em imagem depende de servico online"
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff")
    },
    **{
        ext: "Transcricao de audio depende de servico online"
        for ext in (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".avi", ".mkv")
    },
}

# Teto de arquivos por operacao de arraste. Existe para o caso de alguem
# soltar a raiz de um disco na janela: melhor avisar que veio coisa demais
# do que congelar varrendo 200 mil arquivos.
MAX_ARQUIVOS = 500


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def rejection_reason(path: Path) -> str:
    """Motivo, em portugues, para o arquivo nao entrar na fila."""
    ext = path.suffix.lower()
    if ext in REJECTED:
        return REJECTED[ext]
    if not ext:
        return "Arquivo sem extensao, nao da para saber o formato"
    return f"O formato {ext} nao e suportado"


def resumo_formatos() -> str:
    """Linha curta para a zona de arraste. Nomes de grupo, nao extensoes."""
    return "  ".join(SUPPORTED)
