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

| Grupo | Extensoes |
|---|---|
| PDF | `.pdf` |
| Word | `.docx` |
| Excel | `.xlsx`, `.xls` |
| PowerPoint | `.pptx` |
| E-mail | `.msg` |
| Web | `.html`, `.htm` |
| Dados | `.csv`, `.json`, `.xml` |
| Livro | `.epub` |
| Texto | `.txt`, `.md`, `.markdown` |
| Pacote | `.zip` contendo qualquer um dos acima |

Imagens e audio **nao** sao convertidos, de proposito. Extrair texto de
imagem ou transcrever audio depende de servico online, e o app abriu mao
dos dois em troca de funcionar sem internet. Ao soltar um `.png` ou um
`.mp3`, o app diz exatamente isso, em vez de falhar em silencio.

## Como usar

### 1. Coloque os arquivos na fila

Ha tres jeitos, e todos aceitam varios arquivos de uma vez:

- **Arraste do Explorer para qualquer lugar da janela.** Nao precisa mirar
  na area tracejada; a janela inteira aceita.
- **Arraste uma pasta.** Ela entra inteira, incluindo subpastas. Pastas
  ocultas sao ignoradas, e arquivos que o app nao converte sao deixados de
  fora sem encher a tela de aviso.
- **Clique na area tracejada** para abrir o seletor de arquivos. Se estiver
  navegando por teclado, Tab ate a area e Enter faz o mesmo.

O que nao entra aparece numa faixa de aviso com o motivo. Arrastar um
arquivo que ja esta na fila nao cria duplicata. O teto e de 500 arquivos
por arraste, para o caso de alguem soltar a raiz de um disco na janela.

### 2. Escolha onde salvar

**Este passo e obrigatorio.** O app nao adivinha um destino: clicar em
Converter sem escolher pasta mostra o aviso "Escolha a pasta de destino
antes de converter" e nada acontece.

Use o botao **Escolher pasta**, ou arraste uma pasta direto para a barra
de destino no topo. Arrastar um *arquivo* para essa barra tambem funciona
e usa a pasta que o contem.

A escolha e lembrada entre sessoes. Se a pasta for apagada ou renomeada
depois, o app volta a pedir uma, em vez de falhar na abertura.

### 3. Converta

Clique em **Converter**. Ate 4 arquivos sao convertidos ao mesmo tempo, ou
menos se a maquina tiver menos nucleos. O rodape mostra quantos ja
terminaram e quantos falharam.

`livro_cavalos.pdf` vira `livro_cavalos_convertido.md`. Se esse nome ja
existir na pasta de destino, o proximo vira `livro_cavalos_convertido (2).md`,
no estilo do Windows. Isso vale inclusive quando dois arquivos da mesma
fila disputam o mesmo nome, por exemplo `doc.pdf` e `doc.docx`: um fica
com `doc_convertido.md` e o outro com `doc_convertido (2).md`. Nada e
sobrescrito em silencio.

### Enquanto converte

- **Pausar** para o envio de novos arquivos. O que ja esta convertendo
  termina, porque interromper no meio deixaria arquivo pela metade. O
  botao vira **Retomar**.
- **Limpar fila** tira tudo que nao esta convertendo naquele instante.
- **Arraste um item pela lista** para mudar a ordem de conversao.
- **Fechar a janela** durante a conversao e seguro: o app espera os
  arquivos em andamento terminarem antes de sair.

### O que cada estado quer dizer

Todo estado aparece com icone, texto e cor ao mesmo tempo, nunca so cor.
O botao a direita da linha muda conforme o estado:

| Estado | O que aconteceu | Botao da linha |
|---|---|---|
| Aguardando | esta na fila, ainda nao comecou | remover da fila |
| Convertendo | em andamento, com barra indeterminada | nenhum |
| Concluido | virou Markdown com sucesso | abrir o arquivo gerado |
| Falhou | com a explicacao do motivo ao lado | tentar de novo |
| Cancelado | removido antes de converter | remover da fila |

A barra do item em conversao e indeterminada porque a biblioteca nao
informa progresso parcial, e desenhar uma porcentagem inventada seria
mentir sobre quanto falta.

### Quando algo da errado

A mensagem na linha e escrita para ser entendida sem conhecimento tecnico.
Quando existe informacao tecnica por tras, aparece o botao **Ver detalhes**,
que abre o texto cru para quem precisa investigar.

Dois casos que confundem e merecem explicacao:

- **"Nao foi possivel ler o arquivo. Ele pode estar corrompido ou protegido
  por senha."** O app nao pede senha de PDF. Remova a protecao antes.
- **"Nenhum texto foi encontrado. O arquivo pode ser digitalizado."** O
  arquivo converteu sem erro, mas nao tinha texto dentro: e o caso do
  documento escaneado, que na pratica e uma foto. Ler texto de imagem
  exigiria enviar o arquivo para um servico online, o que este app nao faz.
  O `.md` e gerado mesmo assim, vazio, e o aviso fica visivel na linha.

Depois de corrigir o problema, clique em **tentar de novo** na propria
linha, sem precisar arrastar o arquivo outra vez.

### Conversoes recentes

A aba **Recentes** guarda o que voce ja converteu, com data e hora, quanto
texto saiu de cada arquivo e o motivo de quem falhou. Clique duas vezes
numa linha, ou use **Abrir convertido**, para abrir o `.md` resultante.

O historico e **local e so seu**: fica num banco SQLite em
`%LOCALAPPDATA%\MarkItDown\historico.db`, nada e enviado para lugar
nenhum. Ele guarda os ultimos 500 registros e descarta os mais antigos
sozinho, para nao crescer no seu disco sem fim.

O botao **Apagar historico** limpa a lista por completo. Ele apaga apenas
o registro de que a conversao aconteceu; os arquivos convertidos
continuam onde estao.

### Tema claro e escuro

O app **segue o tema do Windows** sozinho, sem opcao para configurar. Se o
sistema estiver no modo escuro, ele abre escuro. Trocar o tema do Windows
com o app aberto tambem funciona.

O tema escuro nao e o claro invertido: as superficies sao um verde-azulado
profundo da mesma familia da paleta, e o Mint Leaf continua sendo a cor de
acao. Os mesmos 14 pares de contraste sao medidos por teste nos dois
temas, entao a acessibilidade nao vale so no claro.

### Uso so pelo teclado

A janela inteira e navegavel por Tab, com anel de foco visivel em todo
controle. Na area de arraste, Enter ou Espaco abre o seletor de arquivos.
Todo botao que mostra so um icone tem nome acessivel que inclui o nome do
arquivo afetado, por exemplo "Remover da fila: relatorio.pdf".

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

## Instalar

Rode `MarkItDown-Setup.exe`, um arquivo so, com cerca de 83 MB. O
assistente pergunta onde instalar, se voce quer atalhos e se quer o
programa no PATH. **Nao pede senha de administrador**, nao precisa de
internet e nao precisa de Python.

O destino padrao e `%LOCALAPPDATA%\Programs\MarkItDown`, que e a pasta
que o Windows reserva para programas de um usuario so. Depois de
instalado, o MarkItDown aparece em Aplicativos Instalados e sai por la,
como qualquer outro programa: a desinstalacao remove a pasta, os atalhos,
o registro e tambem a entrada que tiver criado no PATH.

Uma limitacao vale saber: **a pasta de destino nao pode passar de 158
caracteres.** O Windows corta caminhos em 260, e alguns arquivos internos
deste programa ja usam mais de cem. O instalador confere isso na hora de
escolher a pasta e explica o motivo, em vez de falhar no meio da copia.

### Gerar o instalador a partir do codigo

```
.venv\Scripts\python.exe -m installer.build_setup
```

Ele usa o Inno Setup, se estiver instalado, e produz um `.exe` unico em
`dist/MarkItDown-Setup.exe`. Para instalar o Inno Setup:

```
winget install --id JRSoftware.InnoSetup --exact
```

Sem o Inno Setup o script continua funcionando, mas cai para um instalador
em pasta, entregue como `dist/MarkItDown-Setup.zip`. Funciona igual, so
que sao dois arquivos e o resultado fica bem maior, em torno de 142 MB.

## Gerar o executavel

```
.venv\Scripts\python.exe build.py
```

Sai em `dist/MarkItDown/MarkItDown.exe`, com cerca de 268 MB. O tamanho e
quase todo modelo de deteccao de tipo de arquivo (`magika`) e runtime
nativo (`onnxruntime`), que sao o preco de identificar formato sem
consultar servico online.

O `build.py` gera o icone a partir dos proprios tokens de design, entao
nao ha arquivo de imagem vindo de fora que possa ficar dessincronizado do
tema.

## Estrutura do repositorio

```
markitdown_gui/      o aplicativo
  core/              Python puro, sem Qt. E o que da para testar sem janela
  jobs/              orquestracao da fila, ponte entre o core e a interface
  ui/                tudo que desenha
  resources/fonts/   fontes embarcadas, opcionais

installer/           o instalador, com a mesma separacao em camadas
tests/               a suite, um arquivo por modulo
docs/                decisoes, auditoria de acessibilidade e planos
resources/           o icone do executavel, gerado por build.py
```

### `markitdown_gui/core/`, Python puro

Nao importa Qt, e isso e verificado por teste. E o que torna a logica
testavel em segundos, sem abrir janela.

| Arquivo | O que resolve |
|---|---|
| `formats.py` | quais extensoes entram, e o motivo em portugues das que nao entram. Fonte unica: nao existe segunda lista em lugar nenhum |
| `naming.py` | `livro.pdf` vira `livro_convertido.md`, e resolve colisao com ` (2)`, inclusive entre dois arquivos da mesma fila |
| `discovery.py` | expande pastas recursivamente, remove duplicata, ignora pasta oculta e aplica o teto de 500 arquivos |
| `converter.py` | camada fina sobre a biblioteca `markitdown`. Uma instancia por thread, a trava de privacidade, e a traducao de excecao tecnica para frase que um humano entende |
| `historico.py` | o registro local das conversoes, em SQLite. Engole os proprios erros de proposito: historico nao pode derrubar conversao |

### `markitdown_gui/jobs/`, a fila

Conhece Qt e conhece o core. O core nao conhece nenhum dos dois.

| Arquivo | O que resolve |
|---|---|
| `models.py` | o que e um item da fila e quais estados ele tem. Sem Qt |
| `worker.py` | a unidade de trabalho que roda fora da thread da interface |
| `controller.py` | o cerebro da fila. Despacha ate 4 conversoes, e **escolhe o nome de saida na thread da interface**, que e o que elimina a corrida entre workers |

O pacote se chama `jobs` e nao `queue` de proposito: `queue` e um modulo
da biblioteca padrao, e sombrear ele quebra o empacotamento.

### `markitdown_gui/ui/`, a interface

Só desenha e conecta sinais. Nenhuma regra de negocio, e nenhuma cor
literal fora do `theme.py`, verificado por teste.

| Arquivo | O que resolve |
|---|---|
| `theme.py` | **a unica fonte de cor do projeto**. As duas paletas, clara e escura, os tokens de espaco e tipografia, e a folha de estilo inteira |
| `icons.py` | os icones em SVG, escritos no proprio modulo, recoloridos em tempo de execucao. Tambem desenha a marca do app |
| `drop_zone.py` | a area de arraste, grande quando a fila esta vazia e faixa fina quando ha itens |
| `destino_bar.py` | a barra de destino, que tambem aceita pasta solta |
| `queue_row.py` | uma linha da fila, com icone, texto e cor para cada estado |
| `queue_view.py` | a lista, que reordena por arraste e recebe arquivos de fora |
| `history_view.py` | a aba de conversoes recentes |
| `prefs.py` | a pasta de destino e a geometria da janela, via QSettings |
| `main_window.py` | o integrador. Monta as abas e liga sinal em slot |

### `installer/`

Mesma separacao em camadas, pelo mesmo motivo: o que mexe no computador
de quem instala precisa ser testavel.

| Arquivo | O que resolve |
|---|---|
| `nucleo.py` | logica pura: PATH sem duplicar, destino seguro, verificacao de integridade, caminho longo do Windows. E o que tem teste |
| `windows.py` | as chamadas que mexem de verdade no sistema: registro, atalhos, PATH |
| `setup_app.py` | o assistente em tkinter, usado so quando nao ha Inno Setup |
| `markitdown.iss` | o script do Inno Setup, que gera o `Setup.exe` de arquivo unico |
| `build_setup.py` | monta tudo, e **detecta build obsoleto** para nao empacotar codigo velho |

### Raiz

| Arquivo | O que resolve |
|---|---|
| `main.py` | ponto de entrada do app |
| `build.py` | empacota o app com PyInstaller e gera o icone |
| `MarkItDown.spec` | receita do PyInstaller, gerada e versionada |
| `pyproject.toml` | metadados e configuracao do pytest |
| `requirements.txt` | as duas dependencias de execucao |
| `requirements-dev.txt` | pytest e PyInstaller |

Nao versionados, porque sao gerados: `dist/`, `build/`, `.venv/` e
`tests/fixtures/formatos/`.

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
