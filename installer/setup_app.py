"""O assistente de instalacao do MarkItDown.

Interface em tkinter, e nao em Qt, de proposito: o Qt ja vai dentro da
carga comprimida, e embutir uma segunda copia so para desenhar quatro
telas somaria dezenas de megabytes a um instalador que ja e grande. O
tkinter vem com o Python e custa quase nada.

Fluxo: escolher pasta, escolher opcoes, instalar, verificar, terminar.
Nada de administrador, nada de rede.
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import nucleo, windows

PACOTE = "MarkItDown-payload.zip"
ARQUIVO_VERSAO = "versao.txt"

# Cores da identidade do app, para o instalador nao parecer de outro
# programa. Sao as mesmas de ui/theme.py, repetidas aqui porque o
# instalador nao importa nada do pacote do app: ele precisa rodar antes
# de o app existir na maquina.
FUNDO = "#FFFBFA"
TINTA = "#0B2B33"
TINTA_FRACA = "#33565C"
PRIMARIA = "#00BD9D"
ALERTA = "#B3261E"


def _candidatos_de_dados() -> list[Path]:
    """Onde procurar o pacote, em ordem de preferencia.

    O pacote fica AO LADO do executavel, e nao embutido nele. A razao e
    medida, nao teorica: um executavel unico de mais de cem megabytes trava
    na descompactacao nesta classe de maquina, provavelmente barrado pela
    protecao em tempo real ao gravar centenas de arquivos no temporario. A
    extracao para no meio, o processo fica vivo e nada acontece. Um
    executavel pequeno com o pacote ao lado nao passa por isso, porque o
    bootloader so descompacta o proprio interpretador.
    """
    lugares: list[Path] = []
    if getattr(sys, "frozen", False):
        lugares.append(Path(sys.executable).resolve().parent)
        embutido = getattr(sys, "_MEIPASS", None)
        if embutido:
            lugares.append(Path(embutido))
    else:
        lugares.append(Path(__file__).resolve().parent.parent / "dist")
    return lugares


def _achar(nome: str) -> Path:
    for lugar in _candidatos_de_dados():
        alvo = lugar / nome
        if alvo.exists():
            return alvo
    return _candidatos_de_dados()[0] / nome


def _raiz_dos_dados() -> Path:
    return _candidatos_de_dados()[0]


def _ler_versao() -> str:
    try:
        return _achar(ARQUIVO_VERSAO).read_text(encoding="utf-8").strip() or "1.0.0"
    except OSError:
        return "1.0.0"


class Assistente(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.versao = _ler_versao()
        self.pacote = _achar(PACOTE)

        self.title(f"Instalar {nucleo.APP}")
        self.configure(bg=FUNDO)
        self.resizable(False, False)
        self.geometry("560x420")

        self.destino = tk.StringVar(value=str(nucleo.destino_padrao()))
        self.atalho_area = tk.BooleanVar(value=True)
        self.atalho_menu = tk.BooleanVar(value=True)
        self.no_path = tk.BooleanVar(value=False)
        self.abrir_ao_final = tk.BooleanVar(value=True)
        self._instalando = False

        self._montar()
        self._checar_pacote()

    # ---------------------------------------------------------- layout

    def _montar(self) -> None:
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("vista")
        except tk.TclError:
            pass
        estilo.configure("TFrame", background=FUNDO)
        estilo.configure("TLabel", background=FUNDO, foreground=TINTA)
        estilo.configure("TCheckbutton", background=FUNDO, foreground=TINTA)

        raiz = ttk.Frame(self, padding=24)
        raiz.pack(fill="both", expand=True)

        tk.Label(
            raiz,
            text=nucleo.APP,
            bg=FUNDO,
            fg=TINTA,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            raiz,
            text=f"Converte documentos para Markdown. Versao {self.versao}.",
            bg=FUNDO,
            fg=TINTA_FRACA,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            raiz,
            text="Funciona sem internet. Nao precisa de Python instalado.",
            bg=FUNDO,
            fg=TINTA_FRACA,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 16))

        ttk.Label(raiz, text="Instalar em:").pack(anchor="w")
        linha = ttk.Frame(raiz)
        linha.pack(fill="x", pady=(4, 16))
        self.campo = ttk.Entry(linha, textvariable=self.destino)
        self.campo.pack(side="left", fill="x", expand=True)
        ttk.Button(linha, text="Procurar", command=self._escolher).pack(
            side="left", padx=(8, 0)
        )

        ttk.Checkbutton(
            raiz, text="Criar atalho na area de trabalho",
            variable=self.atalho_area,
        ).pack(anchor="w")
        ttk.Checkbutton(
            raiz, text="Criar atalho no menu Iniciar", variable=self.atalho_menu
        ).pack(anchor="w")
        ttk.Checkbutton(
            raiz,
            text="Adicionar ao PATH, para chamar pelo terminal",
            variable=self.no_path,
        ).pack(anchor="w", pady=(0, 16))

        self.barra = ttk.Progressbar(raiz, mode="determinate", maximum=100)
        self.barra.pack(fill="x")
        self.recado = tk.Label(
            raiz, text="", bg=FUNDO, fg=TINTA_FRACA, font=("Segoe UI", 9),
            anchor="w", justify="left", wraplength=500,
        )
        self.recado.pack(fill="x", pady=(6, 0))

        rodape = ttk.Frame(raiz)
        rodape.pack(side="bottom", fill="x", pady=(16, 0))
        self.botao_sair = ttk.Button(rodape, text="Cancelar", command=self._sair)
        self.botao_sair.pack(side="right")
        self.botao_instalar = ttk.Button(
            rodape, text="Instalar", command=self._instalar
        )
        self.botao_instalar.pack(side="right", padx=(0, 8))

    # ----------------------------------------------------------- apoio

    def _checar_pacote(self) -> None:
        if not self.pacote.exists():
            self._dizer(
                f"Pacote nao encontrado: {PACOTE}. Ele precisa estar na mesma "
                f"pasta deste instalador.",
                erro=True,
            )
            self.botao_instalar.state(["disabled"])

    def _dizer(self, texto: str, erro: bool = False) -> None:
        self.recado.configure(text=texto, fg=ALERTA if erro else TINTA_FRACA)
        self.update_idletasks()

    def _escolher(self) -> None:
        escolhida = filedialog.askdirectory(title="Onde instalar")
        if escolhida:
            self.destino.set(str(Path(escolhida) / nucleo.APP))

    def _sair(self) -> None:
        if self._instalando:
            if not messagebox.askyesno(
                "Cancelar",
                "A instalacao esta em andamento. Sair agora deixa arquivos "
                "pela metade. Sair mesmo assim?",
            ):
                return
        self.destroy()

    # -------------------------------------------------------- instalar

    def _instalar(self) -> None:
        destino = Path(self.destino.get().strip())
        if not nucleo.destino_seguro(destino):
            messagebox.showerror(
                "Pasta invalida",
                "Escolha uma pasta vazia, ou uma instalacao anterior do "
                f"{nucleo.APP}.\n\nNao da para instalar na raiz de um disco "
                "nem em cima de uma pasta que ja tem outros arquivos, porque "
                "a desinstalacao apaga a pasta inteira.",
            )
            return

        self._instalando = True
        self.botao_instalar.state(["disabled"])
        self.campo.state(["disabled"])
        threading.Thread(target=self._trabalhar, args=(destino,), daemon=True).start()

    def _trabalhar(self, destino: Path) -> None:
        try:
            self._passo_extrair(destino)
            verificacao = nucleo.verificar(destino)
            if not verificacao.completa:
                self.after(0, self._falhou, verificacao.resumo)
                return
            atalhos = self._passo_integrar(destino, verificacao)
            self.after(0, self._terminou, destino, verificacao, atalhos)
        except Exception as exc:                    # nunca morrer calado
            self.after(0, self._falhou, f"{type(exc).__name__}: {exc}")

    def _passo_extrair(self, destino: Path) -> None:
        self.after(0, self._dizer, "Copiando arquivos...")

        def andou(feitos: int, total: int) -> None:
            if total and (feitos % 25 == 0 or feitos == total):
                pct = feitos * 100 // total
                self.after(0, self._progresso, pct, f"Copiando... {feitos} de {total}")

        nucleo.extrair(self.pacote, destino, progresso=andou)

    def _passo_integrar(self, destino: Path, verificacao) -> list[Path]:
        self.after(0, self._progresso, 100, "Criando atalhos...")
        alvo = destino / nucleo.EXECUTAVEL
        atalhos: list[Path] = []

        if self.atalho_area.get():
            lnk = windows.pasta_area_de_trabalho() / f"{nucleo.APP}.lnk"
            if windows.criar_atalho(lnk, alvo, alvo):
                atalhos.append(lnk)
        if self.atalho_menu.get():
            lnk = windows.pasta_menu_iniciar() / f"{nucleo.APP}.lnk"
            if windows.criar_atalho(lnk, alvo, alvo):
                atalhos.append(lnk)

        mexeu_no_path = False
        if self.no_path.get():
            windows.acrescentar_ao_path(destino)
            mexeu_no_path = True

        windows.escrever_desinstalador(destino, atalhos, mexeu_no_path)
        windows.registrar_desinstalacao(
            destino, self.versao, verificacao.bytes_totais // 1024
        )
        return atalhos

    # -------------------------------------------------------- desfecho

    def _progresso(self, pct: int, texto: str) -> None:
        self.barra["value"] = pct
        self._dizer(texto)

    def _falhou(self, motivo: str) -> None:
        self._instalando = False
        self.botao_instalar.state(["!disabled"])
        self.campo.state(["!disabled"])
        self._dizer(f"A instalacao nao terminou. {motivo}", erro=True)
        messagebox.showerror("Nao deu certo", motivo)

    def _terminou(self, destino: Path, verificacao, atalhos: list[Path]) -> None:
        self._instalando = False
        self.barra["value"] = 100
        self._dizer(f"Instalado em {destino}. {verificacao.resumo}.")
        self.botao_sair.configure(text="Fechar")
        self.botao_instalar.configure(
            text="Abrir agora", command=lambda: self._abrir(destino)
        )
        self.botao_instalar.state(["!disabled"])
        if self.abrir_ao_final.get():
            pass  # o usuario decide clicando, para nao roubar o foco dele

    def _abrir(self, destino: Path) -> None:
        windows.abrir(destino / nucleo.EXECUTAVEL)
        self.destroy()


def main() -> int:
    Assistente().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
