"""Gera arquivos de exemplo em formatos binarios reais.

Rodar uma vez: .venv\\Scripts\\python.exe tests/fixtures/gerar_formatos.py

Por que escrever PDF e DOCX na mao em vez de usar uma biblioteca:

O projeto nao depende de gerador de PDF nem de DOCX, e nao faz sentido
adicionar dependencia so para produzir fixture. O `markitdown[docx]` traz
o mammoth, que le e nao escreve, e o QPdfWriter do Qt grava glifos sem
mapa ToUnicode, o que produz um PDF do qual nao se extrai texto nenhum.
Um PDF assim serve para testar o caso do documento digitalizado, mas nao
serve para provar que a conversao funciona.

Os dois formatos abaixo sao minimos e escritos com estruturas
documentadas: PDF com fonte Type1 padrao (Helvetica), que dispensa mapa
de caracteres, e DOCX que e apenas um zip com XML dentro.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

AQUI = Path(__file__).parent

TEXTO_PDF = "Relatorio anual de cavalos"
TEXTO_DOCX = "Contrato de teste com acento: coracao, informacao."


def pdf_com_texto(destino: Path, texto: str) -> Path:
    """PDF minimo com texto extraivel, montado com deslocamentos corretos."""
    conteudo = f"BT /F1 24 Tf 72 700 Td ({texto}) Tj ET\n".encode("latin-1")

    objetos = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(conteudo)).encode() + b">>\nstream\n"
        + conteudo + b"endstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]

    saida = bytearray(b"%PDF-1.4\n")
    deslocamentos = []
    for numero, corpo in enumerate(objetos, start=1):
        deslocamentos.append(len(saida))
        saida += f"{numero} 0 obj\n".encode() + corpo + b"\nendobj\n"

    inicio_xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n".encode()
    saida += b"0000000000 65535 f \n"
    for deslocamento in deslocamentos:
        saida += f"{deslocamento:010d} 00000 n \n".encode()
    saida += (
        f"trailer\n<</Size {len(objetos) + 1}/Root 1 0 R>>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n"
    ).encode()

    destino.write_bytes(bytes(saida))
    return destino


def docx_com_texto(destino: Path, texto: str) -> Path:
    """DOCX minimo: um zip com o XML que o mammoth espera encontrar."""
    tipos = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relacoes = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    documento = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{texto}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", relacoes)
        z.writestr("word/document.xml", documento)
    return destino


def pdf_sem_texto(destino: Path) -> Path:
    """PDF valido cuja pagina nao tem texto nenhum.

    Representa o documento digitalizado: converte sem erro e rende zero
    caracteres. E o caso que o app precisa avisar em vez de calar.
    """
    objetos = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>",
        b"<</Length 0>>\nstream\nendstream",
    ]
    saida = bytearray(b"%PDF-1.4\n")
    deslocamentos = []
    for numero, corpo in enumerate(objetos, start=1):
        deslocamentos.append(len(saida))
        saida += f"{numero} 0 obj\n".encode() + corpo + b"\nendobj\n"
    inicio_xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n".encode()
    saida += b"0000000000 65535 f \n"
    for deslocamento in deslocamentos:
        saida += f"{deslocamento:010d} 00000 n \n".encode()
    saida += (
        f"trailer\n<</Size {len(objetos) + 1}/Root 1 0 R>>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n"
    ).encode()
    destino.write_bytes(bytes(saida))
    return destino


def pdf_corrompido(destino: Path) -> Path:
    """Cabecalho de PDF seguido de lixo. Precisa falhar com mensagem humana."""
    destino.write_bytes(b"%PDF-1.4\n" + b"\x00\xff" * 400)
    return destino


def png_falso(destino: Path) -> Path:
    """PNG valido o bastante para o app reconhecer o formato e recusar."""
    destino.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return destino


def gerar_todos(pasta: Path) -> dict[str, Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    return {
        "pdf": pdf_com_texto(pasta / "relatorio.pdf", TEXTO_PDF),
        "docx": docx_com_texto(pasta / "contrato.docx", TEXTO_DOCX),
        "pdf_vazio": pdf_sem_texto(pasta / "digitalizado.pdf"),
        "pdf_ruim": pdf_corrompido(pasta / "corrompido.pdf"),
        "png": png_falso(pasta / "foto.png"),
    }


if __name__ == "__main__":
    criados = gerar_todos(AQUI / "formatos")
    for papel, caminho in criados.items():
        print(f"{papel:<10} {caminho.name:<22} {caminho.stat().st_size} bytes")
