"""Conjunto de icones do app, desenhado como SVG dentro do proprio modulo.

Duas decisoes explicam o formato deste arquivo.

A primeira: nenhum arquivo de imagem externo. O SVG mora aqui como string,
entao o PyInstaller nao precisa de regra de coleta de dados e o executavel
nao tem como sair sem os icones.

A segunda: nenhum emoji. Emoji muda de desenho conforme a fonte instalada,
nao aceita recoloracao e nao respeita o alinhamento optico do resto da
interface. Os tracos aqui seguem a grade 24x24 no estilo Lucide, com traco
de 2 e pontas arredondadas.

A cor entra em tempo de execucao: o molde declara `stroke="currentColor"`
e `pixmap` troca esse literal pelo token pedido. Cor literal so existe em
`theme.py`, e o padrao daqui e `theme.COLOR["ink"]`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from markitdown_gui.ui import theme

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtGui import QIcon, QPixmap


_MOLDE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">{tracos}</svg>'
)

# Os quinze nomes do contrato 4.3. Nome em portugues, porque quem le a
# chamada no codigo da interface le em portugues.
_TRACOS: dict[str, str] = {
    "arquivo": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 2v6h6"/>'
        '<path d="M16 13H8"/>'
        '<path d="M16 17H8"/>'
        '<path d="M10 9H8"/>'
    ),
    "pasta": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9'
        'L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
    ),
    "pasta-aberta": (
        '<path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5'
        'l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9'
        'a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>'
    ),
    "upload": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<path d="M17 8l-5-5-5 5"/>'
        '<path d="M12 3v12"/>'
    ),
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "alerta": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16'
        'a2 2 0 0 0 1.73-3"/>'
        '<path d="M12 9v4"/>'
        '<path d="M12 17h.01"/>'
    ),
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "repetir": (
        '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
        '<path d="M21 3v5h-5"/>'
        '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
        '<path d="M8 16H3v5"/>'
    ),
    "abrir-externo": (
        '<path d="M15 3h6v6"/>'
        '<path d="M10 14 21 3"/>'
        '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    ),
    "pausar": (
        '<rect x="14" y="4" width="4" height="16" rx="1"/>'
        '<rect x="6" y="4" width="4" height="16" rx="1"/>'
    ),
    "tocar": '<path d="M6 3v18l14-9Z"/>',
    "lixeira": (
        '<path d="M3 6h18"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'
        '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<path d="M10 11v6"/>'
        '<path d="M14 11v6"/>'
    ),
    "arrastar": (
        '<circle cx="9" cy="5" r="1"/>'
        '<circle cx="9" cy="12" r="1"/>'
        '<circle cx="9" cy="19" r="1"/>'
        '<circle cx="15" cy="5" r="1"/>'
        '<circle cx="15" cy="12" r="1"/>'
        '<circle cx="15" cy="19" r="1"/>'
    ),
    "ampulheta": (
        '<path d="M5 22h14"/>'
        '<path d="M5 2h14"/>'
        '<path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414'
        'A2 2 0 0 0 7 17.828V22"/>'
        '<path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414'
        'A2 2 0 0 0 17 6.172V2"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 16v-4"/>'
        '<path d="M12 8h.01"/>'
    ),
}

NOMES: tuple[str, ...] = tuple(_TRACOS)

# Renderizar SVG nao e de graca e a fila pede o mesmo icone linha apos
# linha, entao o resultado fica em cache pela combinacao que o define.
_CACHE: dict[tuple[str, str, int, float], "QPixmap"] = {}


def _svg(nome: str, cor: str) -> str:
    """Molde com os tracos do icone e a cor ja resolvida."""
    return _MOLDE.format(tracos=_TRACOS[nome]).replace("currentColor", cor)


def _escala() -> float:
    """Fator de tela, para o icone nao sair borrado em monitor HiDPI."""
    try:
        from PySide6.QtGui import QGuiApplication

        tela = QGuiApplication.primaryScreen()
        if tela is not None:
            return float(tela.devicePixelRatio())
    except Exception:
        pass
    return 1.0


def limpar_cache() -> None:
    """Esvazia o cache de icones ja rasterizados.

    Chamado por theme.definir_tema. Sem isso, trocar para o tema
    escuro deixaria na tela os icones desenhados com as cores do
    tema claro, porque a chave do cache guarda a cor pedida e nao
    sabe que a paleta inteira mudou de significado.
    """
    _CACHE.clear()


def pixmap(
    nome: str,
    cor: str | None = None,
    tamanho: int = 20,
    escala: float | None = None,
) -> "QPixmap":
    """Icone rasterizado no tamanho pedido, com fundo transparente.

    Nome fora do conjunto levanta KeyError de proposito: um icone faltando
    precisa aparecer como erro, nao como quadrado vazio na interface.

    `escala` normalmente fica em None, e ai o fator vem da tela, que e o
    certo para nao sair borrado em monitor HiDPI. Quem esta gerando
    ARQUIVO, e nao pixel de tela, precisa passar 1.0: um `.ico` quer
    pixels exatos, e deixar a tela decidir faria o mesmo comando produzir
    bytes diferentes em cada maquina.
    """
    if nome not in _TRACOS:
        raise KeyError(
            f"icone desconhecido: {nome!r}. Disponiveis: {', '.join(NOMES)}"
        )

    if cor is None:
        cor = theme.COLOR["ink"]

    if escala is None:
        escala = _escala()
    chave = (nome, cor, tamanho, escala)
    em_cache = _CACHE.get(chave)
    if em_cache is not None:
        return em_cache

    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    lado = max(1, round(tamanho * escala))
    imagem = QPixmap(lado, lado)
    imagem.fill(Qt.GlobalColor.transparent)

    renderizador = QSvgRenderer(QByteArray(_svg(nome, cor).encode("utf-8")))
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderizador.render(pintor)
    pintor.end()

    imagem.setDevicePixelRatio(escala)
    _CACHE[chave] = imagem
    return imagem


def icone(nome: str, cor: str | None = None, tamanho: int = 20) -> "QIcon":
    """O mesmo desenho de `pixmap`, embrulhado para uso em botao e item."""
    from PySide6.QtGui import QIcon

    return QIcon(pixmap(nome, cor, tamanho))


# Tamanhos que o Windows pede: barra de titulo, barra de tarefas, Alt+Tab
# e a visualizacao grande do Explorer.
TAMANHOS_DO_APP = (16, 24, 32, 48, 64, 128, 256)


def marca(tamanho: int = 256, escala: float | None = None) -> "QPixmap":
    """O simbolo do aplicativo: quadrado arredondado com o glifo dentro.

    Esta funcao e a unica fonte do desenho. A janela chama daqui e o
    `build.py` chama daqui para gerar o `.ico` do executavel, entao o
    icone da barra de tarefas nunca fica diferente do icone do arquivo.
    Antes o desenho existia so no build, e a janela ficava com o icone
    generico do Qt.

    As cores saem de `theme.COLOR`, entao a marca acompanha a paleta. Na
    pratica ela quase nao muda entre os temas: o Mint Leaf e o mesmo nos
    dois e o glifo e escuro nos dois.
    """
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QPainter, QPixmap

    if escala is None:
        escala = _escala()
    lado = max(1, round(tamanho * escala))

    imagem = QPixmap(lado, lado)
    imagem.fill(Qt.GlobalColor.transparent)

    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(QBrush(QColor(theme.COLOR["primary"])))
    raio = lado * 0.22
    pintor.drawRoundedRect(QRectF(0, 0, lado, lado), raio, raio)

    glifo = max(8, int(lado * 0.56))
    dentro = pixmap("arquivo", theme.COLOR["on_primary"], glifo, escala=1.0)
    pintor.drawPixmap(
        int((lado - dentro.width()) / 2),
        int((lado - dentro.height()) / 2),
        dentro,
    )
    pintor.end()

    imagem.setDevicePixelRatio(escala)
    return imagem


def icone_do_app() -> "QIcon":
    """A marca em todos os tamanhos que o Windows costuma pedir.

    Um QIcon com varios tamanhos deixa o Windows escolher o melhor para
    cada lugar, em vez de esticar um so e sair borrado no Alt+Tab.
    """
    from PySide6.QtGui import QIcon

    icone_pronto = QIcon()
    for lado in TAMANHOS_DO_APP:
        icone_pronto.addPixmap(marca(lado, escala=1.0))
    return icone_pronto
