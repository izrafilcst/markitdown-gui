# MarkItDown

Aplicativo de desktop para Windows que converte documentos para Markdown
usando a biblioteca [markitdown](https://github.com/microsoft/markitdown)
da Microsoft. Arraste arquivos ou pastas, escolha onde salvar, converta.

**Funciona 100% offline.** Nenhum arquivo sai da sua maquina, e isso nao e
so uma promessa de texto: `tests/test_offline.py` bloqueia a criacao de
sockets e converte arquivos reais com a rede proibida, e uma varredura
estatica reprova o build se qualquer cliente HTTP for sequer mencionado no
codigo.

## O que ele converte

PDF, DOCX, PPTX, XLSX, XLS, mensagens do Outlook, HTML, CSV, JSON, XML,
arquivos de texto e ZIP contendo esses formatos.

Imagens e audio **nao** sao convertidos. A biblioteca so extrai conteudo
desses formatos com ajuda de servico online, e o app abre mao disso em
troca de funcionar sem internet. Ao soltar uma imagem, o app explica o
motivo em vez de falhar em silencio.

## Como usar

1. Arraste arquivos ou pastas para a janela. Pastas entram inteiras,
   incluindo subpastas.
2. Escolha a pasta de destino, ou arraste uma pasta para a barra de
   destino. Sem escolher, o arquivo convertido fica ao lado do original.
3. Clique em Converter.

O arquivo `livro_cavalos.pdf` vira `livro_cavalos_convertido.md`. Se esse
nome ja existir, o proximo vira `livro_cavalos_convertido (2).md`, no
estilo do Windows.

Ate 4 arquivos sao convertidos ao mesmo tempo. A pasta de destino e
lembrada entre sessoes.

## Rodar a partir do codigo

```
.venv\Scripts\python.exe main.py
```

Testes:

```
.venv\Scripts\python.exe -m pytest tests/ -q
```

Os testes de interface rodam sem abrir janela, com
`QT_QPA_PLATFORM=offscreen`, que o `tests/conftest.py` ja define.

## Arquitetura

Tres camadas, com dependencia em sentido unico:

```
ui/     desenha e conecta sinais, nenhuma regra de negocio
  |
jobs/   orquestra um QThreadPool de ate 4 workers, traduz para sinais Qt
  |
core/   Python puro, nao importa Qt, e por isso testavel sem abrir janela
```

Tres regras estruturais sao verificadas por teste e nao por disciplina:

- `core/` nunca importa Qt.
- Nenhum modulo menciona cliente HTTP.
- Cor literal em hexadecimal so existe em `ui/theme.py`.

A biblioteca `markitdown` e dependencia pip, nunca codigo copiado. Subir
de versao e trocar uma linha no `requirements.txt`.

## Uma decisao que vale explicar

O nome do arquivo de saida e escolhido **na thread da interface**, no
momento em que o trabalho e despachado, e nao dentro do worker. Parece
detalhe e nao e: com quatro workers em paralelo, deixar cada um escolher o
proprio nome cria corrida entre eles, e dois arquivos com o mesmo nome base
sobrescrevem um ao outro de forma intermitente. Serializar a decisao no
despacho elimina a classe inteira de bug. `tests/test_controller.py` cobra
isso convertendo `doc.csv` e `doc.json` ao mesmo tempo.

## Documentacao

- `docs/acessibilidade.md`: tabela de contraste medida e a justificativa do
  token `ink`.
- `docs/design.md`: decisoes de produto e arquitetura.
- `docs/PLANO-EXECUCAO.md`: contratos congelados entre modulos.
