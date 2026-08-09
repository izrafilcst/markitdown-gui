# Design e decisoes

## Aviso sobre a procedencia deste documento

O plano de implementacao pede que esta pagina carregue o Understanding
Lock, as premissas e o Decision Log **completos** da sessao de
brainstorming original. Essa sessao nao esta versionada neste repositorio,
e a sessao de execucao que escreveu este arquivo nao teve acesso a ela.

Em vez de reconstruir de memoria e apresentar invencao como registro, o
que esta abaixo e reconstruido **apenas** a partir de fontes verificaveis:
`docs/PLANO-EXECUCAO.md`, `docs/plans/2026-08-07-markitdown-gui.md`, e as
decisoes tomadas durante a implementacao, que estao no codigo e nos
commits. As decisoes marcadas com **[origem: brainstorming]** aparecem
justificadas nos documentos de plano; as marcadas com
**[origem: execucao]** foram tomadas ao implementar. Falta o registro das
alternativas descartadas na sessao original, e essa lacuna e real.

## 1. Problema

Converter documentos para Markdown, para um usuario nao tecnico, no
Windows, sem que nada saia da maquina.

A biblioteca `markitdown` da Microsoft ja resolve a conversao. O que nao
existe e uma forma de um usuario comum usa-la: a biblioteca e uma API
Python e uma linha de comando. O produto aqui e a interface, nao a
conversao.

## 2. Premissas

1. O usuario nao sabe abrir um terminal.
2. Ele tem os arquivos abertos no Explorer e vai arrasta-los.
3. Ele converte em lote, nao um por vez.
4. A maquina pode estar sem internet, e o conteudo pode ser sensivel.
5. Windows e o unico alvo. Nada foi verificado em macOS ou Linux.

## 3. Decision Log

### D1. Qt em vez de interface web  **[origem: brainstorming]**

Uma interface HTML nao recebe o caminho absoluto de um arquivo solto, so o
conteudo. Converter um lote de PDFs grandes exigiria copiar tudo para uma
pasta temporaria antes de comecar.

Esta decisao foi tratada como **premissa a ser testada, nao como fato**:
`tests/test_drop.py::test_drop_entrega_caminho_absoluto` existe para
provar que a escolha se sustenta. Se ele falhar algum dia, a decisao
estava errada.

### D2. Zero rede, custe o que custar  **[origem: brainstorming]**

O `markitdown` sabe descrever imagens e transcrever audio, e faz isso
chamando servico externo. O app abre mao dos dois.

A promessa virou mecanismo em tres camadas: `enable_plugins=False` na
instancia da biblioteca, um teste que proibe `socket.socket` e converte
mesmo assim, e uma varredura estatica que reprova se o codigo mencionar
qualquer cliente HTTP. Promessa que nao e verificavel por maquina nao e
promessa, e comentario.

### D3. `markitdown` e dependencia, nunca codigo copiado  **[origem: brainstorming]**

`core/converter.py` tem menos de 150 linhas e existe so para tres coisas
que a biblioteca nao da: uma instancia por thread, a trava de privacidade,
e a traducao de excecao tecnica para frase que um humano entende. Subir de
versao e trocar uma linha no `requirements.txt`.

### D4. O nucleo nao conhece Qt  **[origem: brainstorming]**

`core/` e Python puro. Isso torna a logica de nomeacao, descoberta e
conversao testavel sem abrir janela, e e a razao de a suite rodar em
segundos. A regra e verificada por `test_core_nao_importa_qt`.

Durante a execucao esse teste acusou o proprio `core/__init__.py`, cuja
docstring citava o literal do import de Qt ao explicar a regra. A correcao
foi reescrever a docstring, nao afrouxar o teste.

### D5. Nome de saida decidido na thread da interface  **[origem: brainstorming]**

O ponto mais sutil do projeto. Com quatro workers em paralelo, deixar cada
um resolver o proprio nome de destino cria corrida: `doc.csv` e `doc.json`
querem os dois `doc_convertido.md`, e a checagem de existencia em disco
nao pega isso, porque o primeiro ainda nao foi gravado quando o segundo
resolve.

A alocacao acontece no despacho, na thread da interface, com um conjunto
de nomes ja reservados. Isso serializa a decisao sem serializar o trabalho.
`test_nomes_nao_colidem_entre_workers` cobra exatamente esse caso.

### D6. A paleta do cliente e de superficies, e precisou de uma cor nova  **[origem: brainstorming]**

Nenhuma das cinco cores da paleta original passa como cor de texto, e
branco por cima delas tambem nao. A cor `ink` `#0B2B33` foi acrescentada.
A medicao completa esta em `docs/acessibilidade.md`.

### D7. Sem barra de progresso por arquivo  **[origem: brainstorming]**

O `markitdown` nao reporta progresso parcial. Uma barra que anda sozinha
seria mentira sobre quanto falta, entao item em conversao usa barra
indeterminada, e o progresso agregado conta arquivos concluidos.

### D8. Remover nao aparece durante a conversao  **[origem: brainstorming]**

Nao ha como matar uma thread em Python. Em vez de oferecer um botao de
cancelar que nao cancela, o botao simplesmente nao aparece enquanto o item
converte.

### D9. Um botao de acao que troca de papel  **[origem: execucao]**

A linha da fila tem um unico botao que vira remover, repetir ou abrir,
em vez de tres botoes aparecendo e sumindo. Mantem a posicao do alvo de
clique estavel enquanto o estado muda, o que importa para quem tem
dificuldade motora.

### D10. `definir_destino` da barra nao emite sinal  **[origem: execucao]**

O setter reflete estado; ele nao dispara acao. Se emitisse
`destino_escolhido`, a janela principal devolveria ao controller o destino
que o controller acabou de mandar, e viraria laco. Ha teste travando isso.

### D11. Soltar arquivo na barra de destino usa a pasta dele  **[origem: execucao]**

Recusar seria tecnicamente defensavel e praticamente inutil: a intencao de
quem faz esse gesto e obvia, e recusar so faria repetir o gesto no lugar
certo.

### D12. Abrir pasta sem `QDesktopServices`  **[origem: execucao]**

No Windows ele as vezes falha em silencio para caminhos com acento, e
falha silenciosa e o pior resultado possivel para um botao que o usuario
acabou de clicar. O app usa `os.startfile` e reporta erro quando ocorre.

### D13. Conversao vazia avisa, em vez de calar  **[origem: execucao]**

Encontrado ao verificar o `.exe`: um PDF sem texto extraivel, que e o caso
do documento digitalizado, faz o `markitdown` devolver string vazia **sem
erro**. O app gravava um `.md` de zero byte e dizia "Concluido".

Para o publico deste app, que nao e tecnico, esse silencio e pior do que
uma falha honesta: a pessoa so descobre ao abrir o arquivo, possivelmente
depois de converter um lote inteiro. Agora o item conclui, o arquivo e
gravado, e a linha explica que nenhum texto foi encontrado e que o arquivo
pode ser digitalizado. O detalhe tecnico diz por que o app nao faz
reconhecimento otico: exigiria enviar o arquivo para um servico online, o
que a decisao D2 proibe.

### D14. Testar a zona de arraste solta, nao pela janela  **[origem: execucao]**

O teste de teclado da zona instancia `DropZone` diretamente. Pela
`MainWindow`, o sinal `clicada` abre o `QFileDialog`, que e modal e trava
o teste para sempre no modo offscreen. Abrir o dialogo e o comportamento
certo do app; o que nao pode e a suite depender dele.

### D15. O tema escuro precisou de um token novo  **[origem: execucao]**

A regra original dizia: "texto sobre accent e sempre `ink`". Ela valia num
app so claro, onde `ink` e escuro. No tema escuro `ink` vira claro, e o
Sky Aqua continua claro, entao a regra produziria 1.77:1, reprovado.

A saida foi `on_accent`, que e escuro nos dois temas. No tema claro ele
vale exatamente o mesmo que `ink`, entao **nenhum numero da auditoria
original mudou**: os 7.45:1 e 9.06:1 continuam iguais. O que mudou foi o
nome do token nos pares auditados, e o teste agora roda parametrizado nas
duas paletas.

Vale registrar como divergencia do contrato: a secao 4.1 lista os pares
com `ink`. A intencao (texto sobre accent precisa passar) esta preservada,
o valor medido no tema claro tambem, mas o nome do token mudou.

### D16. Historico nunca derruba conversao  **[origem: execucao]**

O historico grava em SQLite e engole os proprios erros. Se o banco estiver
corrompido, o disco cheio ou a pasta sem permissao, `registrar` devolve
None e a fila segue. `recentes` devolve lista vazia.

O motivo e uma ordem de prioridade explicita: converter e o produto,
guardar o registro e conveniencia. Perder uma conversao por causa de um
log seria trocar o essencial pelo acessorio. Ha teste para os dois casos,
inclusive com um arquivo que nao e um banco SQLite no lugar do banco.

### D17. Existe botao de apagar o historico  **[origem: execucao]**

O app passa a guardar nome de arquivo do usuario, que e informacao dele.
Quem guarda dado de alguem precisa oferecer o botao de apagar, senao
"local" vira so uma palavra. A confirmacao deixa claro o que o botao faz e
o que ele nao faz: apaga o registro, nao apaga os arquivos convertidos.

## 4. Divergencias encontradas entre o plano e a realidade

Registradas aqui porque quem repetir este plano vai bater nas mesmas.

| Item | O que o plano assume | O que a maquina faz |
|---|---|---|
| `len(spy)`, `spy[0]` | `QSignalSpy` e sequencia | Levanta `TypeError`. Use `count()` e `at()` |
| `QSignalSpy.wait` | funciona para sinal de worker | Segura o GIL, os workers Python nunca rodam. Use `QEventLoop.exec` |
| `QDropEvent(mime)` | o evento segura o mime | Nao segura. Mime coletado vira ponteiro pendurado e derruba o processo |
| `findChildren((A, B))` | aceita tupla de tipos | Levanta `TypeError`. Um tipo por chamada |
| ambiente provisionado | PyInstaller instalado | Nao estava. Foi instalado durante a execucao |
| build so precisa de magika e onnxruntime | numpy sai junto | Falso. Sem `--collect-all numpy` o .exe morre no import |

## 5. Verificacao do executavel

O `.exe` foi construido e testado em pasta sem Python no PATH:

- Primeira tentativa **quebrou**, com `No module named 'numpy._core._exceptions'`.
  A falha aconteceu no import, antes de qualquer janela aparecer. Foi
  corrigida com `--collect-all numpy` em `build.py`.
- Segunda tentativa sobe limpa e sobrevive.
- Conversao real dentro do bundle congelado foi provada com um executavel
  de console construido com as mesmas flags: converteu `exemplo.html` em
  Markdown correto, com `sys.frozen` verdadeiro e o PATH limpo.

Tamanho final: 268 MB, quase tudo modelo do magika e runtime nativo do
onnxruntime.

## 6. O roteiro de verificacao, automatizado ate onde da

`tests/test_roteiro.py` cobre onze dos itens do roteiro do Task 14, com
arquivos binarios de verdade: PDF com texto extraivel, DOCX com acento,
PDF sem texto (o caso do digitalizado), PDF corrompido e PNG. Os quatro
primeiros sao gerados por `tests/fixtures/gerar_formatos.py`, escritos na
mao, porque o projeto nao depende de gerador de PDF nem de DOCX e nao faz
sentido adicionar dependencia so para produzir fixture.

O que ele verifica: tres formatos entram na fila, pasta com subpastas
entra inteira, PNG e recusado com motivo visivel, conversao gera os `.md`
certos com o texto certo, falha mostra mensagem sem jargao, PDF
digitalizado avisa, repetir devolve o item para pendente, pausar segura o
lote de 20, reordenar chega ao controller, Tab alcanca todos os controles,
fechar durante conversao nao deixa worker solto, e a pasta de destino
sobrevive ao fechar e reabrir.

## 7. O que nao esta feito

- **Arraste real vindo do Explorer.** Os testes injetam `QDropEvent`, o
  que prova o tratamento do evento, nao a travessia do sistema
  operacional. Continua sendo trabalho humano.
- Conversao acionada pela **interface grafica do .exe**. O que foi provado
  e que a pilha de conversao funciona congelada; ninguem arrastou um
  arquivo para a janela do executavel.
- **Foco visivel de fato**: o teste confirma que o QSS define o estado de
  foco e usa o token certo, mas ninguem olhou para a tela.
- Leitor de tela e modo de alto contraste do Windows.
- Teste de carga com 100 arquivos reais. O maior lote testado tem 20.
- `markitdown_gui/ui/theme.py` tem 543 linhas, acima do limite de 500 do
  `CLAUDE.md`. A maior parte e a folha de estilo. Fica registrado como
  divida consciente, nao como descuido.
