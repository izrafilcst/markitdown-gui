"""Cria arquivos de exemplo minimos para os testes de conversao.

Rodar uma vez: .venv\\Scripts\\python.exe tests/fixtures/gerar.py

Sobre o .docx: nao ha gerador de .docx neste script. O interpretador do
projeto nao tem python-docx instalado, e o markitdown[docx] traz mammoth,
que so le .docx e nao escreve. Adicionar python-docx apenas para gerar
fixture aumentaria a superficie de dependencia do projeto sem contrapartida.
Os tres formatos abaixo ja exercitam tres conversores diferentes do
markitdown (HTML, tabular e estruturado), que e o que os testes precisam.
Se um .docx real virar necessario, gere ele fora e versione o arquivo aqui.
"""
from pathlib import Path

AQUI = Path(__file__).parent


def html():
    (AQUI / "exemplo.html").write_text(
        "<html><body><h1>Titulo</h1><p>Paragrafo de teste.</p></body></html>",
        encoding="utf-8",
    )


def csv():
    (AQUI / "exemplo.csv").write_text("nome,idade\nAna,30\nBruno,25\n", encoding="utf-8")


def json_():
    (AQUI / "exemplo.json").write_text('{"chave": "valor"}', encoding="utf-8")


if __name__ == "__main__":
    html()
    csv()
    json_()
    print("fixtures geradas em", AQUI)
