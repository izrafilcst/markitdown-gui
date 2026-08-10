"""O dialogo de verificacao de atualizacao.

Ele so aparece quando o usuario pede. O app nunca consulta sozinho ao
abrir, e essa decisao esta travada por teste: um programa que promete
privacidade nao pode telefonar para casa em silencio.

O fluxo tem tres estados e nenhum deles deixa o usuario sem saber o que
esta acontecendo: perguntando, achou algo, nao achou nada ou deu errado.

A consulta roda numa thread separada porque ela pode demorar dez segundos
com internet ruim, e congelar a janela nesse tempo faria o usuario achar
que o app travou.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import APP_VERSION, atualizacao
from . import icons, theme

ALVO_MINIMO = 32


class _Sinais(QObject):
    """Um QRunnable nao e QObject e nao emite sinal, entao ele carrega um.

    Mesmo padrao de `jobs/worker.py`, de proposito: o projeto ja resolve
    trabalho em segundo plano com QThreadPool, e usar QThread aqui criava
    um segundo modelo de concorrencia, com ciclo de vida proprio para
    errar. E foi o que aconteceu: a thread sobrevivia ao dialogo e
    derrubava o processo no encerramento.
    """

    verificou = Signal(object)
    baixou = Signal(object)


class _Consulta(QRunnable):
    """Pergunta a versao publicada, fora da thread da interface."""

    def __init__(self, versao: str, sinais: _Sinais) -> None:
        super().__init__()
        self._versao = versao
        self._sinais = sinais

    @Slot()
    def run(self) -> None:
        try:
            resultado = atualizacao.verificar(versao_instalada=self._versao)
        except Exception:      # nunca deixar excecao escapar de um QRunnable
            resultado = atualizacao.Resultado(
                erro="Nao foi possivel verificar agora. Tente de novo."
            )
        self._sinais.verificou.emit(resultado)


class _Download(QRunnable):
    """Baixa o instalador, fora da thread da interface."""

    def __init__(self, url: str, sinais: _Sinais) -> None:
        super().__init__()
        self._url = url
        self._sinais = sinais

    @Slot()
    def run(self) -> None:
        try:
            pasta = Path(tempfile.gettempdir()) / "MarkItDown-atualizacao"
            caminho = atualizacao.baixar_instalador(self._url, pasta)
        except Exception:
            caminho = None
        self._sinais.baixou.emit(caminho)


class DialogoDeAtualizacao(QDialog):
    """Mostra a versao instalada, consulta a publicada e oferece atualizar."""

    def __init__(self, parent: QWidget | None = None, versao: str = APP_VERSION) -> None:
        super().__init__(parent)
        self.setWindowTitle("Verificar atualizacoes")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.versao_instalada = versao
        self.resultado: atualizacao.Resultado | None = None
        self._caminho_baixado: Path | None = None
        self._sinais = _Sinais()
        self._sinais.verificou.connect(self._ao_verificar)
        self._sinais.baixou.connect(self._ao_baixar)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(1)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(
            theme.SPACE["xl"], theme.SPACE["xl"], theme.SPACE["xl"], theme.SPACE["xl"]
        )
        raiz.setSpacing(theme.SPACE["md"])

        titulo = QLabel("Verificar atualizacoes")
        titulo.setProperty("papel", "secao")

        self.rotulo_instalada = QLabel(f"Versao instalada: {versao}")
        self.rotulo_instalada.setStyleSheet(f"color: {theme.COLOR['ink_soft']};")

        self.rotulo_estado = QLabel("")
        self.rotulo_estado.setWordWrap(True)

        self.barra = QProgressBar()
        self.barra.setRange(0, 0)          # indeterminada enquanto consulta
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(4)
        self.barra.setVisible(False)

        self.notas = QLabel("")
        self.notas.setWordWrap(True)
        self.notas.setVisible(False)
        self.notas.setStyleSheet(f"color: {theme.COLOR['ink_soft']};")

        rodape = QHBoxLayout()
        rodape.setSpacing(theme.SPACE["sm"])

        self.botao_verificar = QPushButton("Verificar agora")
        self.botao_verificar.setMinimumSize(140, ALVO_MINIMO)
        self.botao_verificar.setIcon(icons.icone("repetir", theme.COLOR["ink"]))
        self.botao_verificar.clicked.connect(self.verificar)

        self.botao_atualizar = QPushButton("Baixar e instalar")
        self.botao_atualizar.setObjectName("BotaoPrimario")
        self.botao_atualizar.setMinimumSize(160, 40)
        self.botao_atualizar.setIcon(icons.icone("upload", theme.COLOR["on_primary"]))
        self.botao_atualizar.setVisible(False)
        self.botao_atualizar.clicked.connect(self.baixar_e_instalar)

        self.botao_fechar = QPushButton("Fechar")
        self.botao_fechar.setMinimumSize(110, ALVO_MINIMO)
        self.botao_fechar.clicked.connect(self.reject)

        rodape.addStretch(1)
        rodape.addWidget(self.botao_verificar)
        rodape.addWidget(self.botao_atualizar)
        rodape.addWidget(self.botao_fechar)

        raiz.addWidget(titulo)
        raiz.addWidget(self.rotulo_instalada)
        raiz.addWidget(self.rotulo_estado)
        raiz.addWidget(self.notas)
        raiz.addWidget(self.barra)
        raiz.addLayout(rodape)

        self._dizer(
            "Este app nao verifica atualizacoes sozinho. "
            "Clique em Verificar agora para consultar o GitHub."
        )

    # ------------------------------------------------ leitura para teste

    def texto_do_estado(self) -> str:
        return self.rotulo_estado.text()

    def oferece_atualizacao(self) -> bool:
        # isVisibleTo e nao isVisible: um filho so e 'visivel' quando a
        # janela inteira ja esta na tela, e o dialogo pode ser consultado
        # antes disso.
        return self.botao_atualizar.isVisibleTo(self)

    def caminho_baixado(self) -> Path | None:
        return self._caminho_baixado

    # ------------------------------------------------------------ fluxo

    def _dizer(self, texto: str, erro: bool = False) -> None:
        self.rotulo_estado.setText(texto)
        self.rotulo_estado.setStyleSheet(
            f"color: {theme.COLOR['danger_text' if erro else 'ink']};"
        )

    def _ocupado(self, ocupado: bool) -> None:
        self.barra.setVisible(ocupado)
        self.botao_verificar.setEnabled(not ocupado)
        self.botao_atualizar.setEnabled(not ocupado)

    def verificar(self) -> None:
        """Consulta a versao publicada, fora da thread da interface."""
        self._ocupado(True)
        self._dizer("Consultando o GitHub...")
        self._pool.start(_Consulta(self.versao_instalada, self._sinais))

    def _ao_verificar(self, resultado: atualizacao.Resultado) -> None:
        self._ocupado(False)
        self.resultado = resultado

        if resultado.erro:
            self._dizer(resultado.erro, erro=True)
            return

        if not resultado.disponivel:
            self._dizer(
                f"Voce ja esta na versao mais recente ({resultado.versao})."
            )
            return

        tamanho = f", {resultado.tamanho_legivel}" if resultado.tamanho else ""
        self._dizer(
            f"Versao {resultado.versao} disponivel{tamanho}.\n"
            "O instalador vai abrir e atualizar por cima da instalacao atual. "
            "Seus arquivos convertidos e seu historico nao sao afetados."
        )
        if resultado.notas:
            self.notas.setText(resultado.notas.strip()[:400])
            self.notas.setVisible(True)
        self.botao_atualizar.setVisible(True)

    def baixar_e_instalar(self) -> None:
        if self.resultado is None or not self.resultado.instalador:
            return
        self._ocupado(True)
        self._dizer("Baixando o instalador...")
        self._pool.start(_Download(self.resultado.instalador, self._sinais))

    def _ao_baixar(self, caminho: Path | None) -> None:
        self._ocupado(False)
        if caminho is None:
            self._dizer(
                "Nao foi possivel baixar o instalador. "
                "Verifique sua conexao, ou baixe direto pela pagina do projeto.",
                erro=True,
            )
            return

        self._caminho_baixado = caminho
        self._dizer(
            "Download concluido. O instalador vai abrir agora.\n"
            "Feche o MarkItDown quando ele pedir."
        )
        self._abrir(caminho)

    def encerrar_thread(self) -> None:
        """Espera o trabalho em segundo plano antes de sair.

        Fechar a janela durante uma consulta e caminho normal, nao
        excecao. Sem esperar, o processo cai no encerramento: a suite de
        testes parava de imprimir o resumo final por causa disso.
        """
        self._pool.clear()
        self._pool.waitForDone(3000)

    def closeEvent(self, evento) -> None:
        self.encerrar_thread()
        super().closeEvent(evento)

    def reject(self) -> None:
        self.encerrar_thread()
        super().reject()

    def _abrir(self, caminho: Path) -> None:
        """Executa o instalador baixado.

        Nao passamos /VERYSILENT: o usuario precisa ver o assistente,
        confirmar a pasta e saber o que esta acontecendo. Atualizar em
        silencio um programa que promete transparencia seria contraditorio.
        """
        try:
            if sys.platform == "win32":
                os.startfile(str(caminho))  # noqa: S606
            else:
                subprocess.run(["xdg-open", str(caminho)], check=False)
        except OSError as exc:
            self._dizer(f"Nao foi possivel abrir o instalador: {exc}", erro=True)
