# Auditoria de acessibilidade

Todos os numeros desta pagina foram medidos por maquina contra os tokens
reais de `markitdown_gui/ui/theme.py`, e sao reproduzidos a cada execucao
de `tests/test_contraste.py`. Nenhum valor aqui e estimativa.

## 1. Por que existe o token `ink`

A paleta que o cliente forneceu tem cinco cores: Snow, Sky Aqua, Sky Light,
Pearl Aqua e Mint Leaf. Ela e uma paleta de **superficies**, e isso nao e
uma opiniao de gosto, e uma medicao:

| Cor da paleta | Como texto sobre Snow | Passa 4.5:1 |
|---|---|---|
| Mint Leaf `#00BD9D` | 2.33:1 | nao |
| Sky Aqua `#49C6E5` | 1.95:1 | nao |
| Pearl Aqua `#8BD7D2` | 1.60:1 | nao |
| Sky Light `#54DEFD` | 1.54:1 | nao |

Branco por cima delas tambem falha: branco sobre Mint Leaf da **2.40:1**,
quase metade do minimo. Ou seja, nao havia combinacao legivel dentro da
paleta original.

A saida foi acrescentar uma cor de tinta na mesma familia de matiz,
`ink` `#0B2B33`, que da 14.52:1 sobre Snow. Dai vem a regra que todo
codigo de interface obedece: **Sky Aqua, Sky Light, Pearl Aqua e Mint Leaf
so aparecem como preenchimento de area, e texto ou icone em cima delas e
sempre `ink`.**

O teste `test_texto_do_botao_primario_nao_e_branco` existe justamente para
impedir que alguem, em uma sessao futura, "simplifique" isso trocando
`on_primary` por branco.

## 2. Tabela de contraste medida

Os 14 pares abaixo sao os declarados em `theme.PARES_AUDITADOS`, e cada um
e um caso de teste parametrizado.

| Frente | Fundo | Medido | Minimo | Resultado |
|---|---|---|---|---|
| `ink` #0B2B33 | `bg` #FFFBFA | 14.52:1 | 4.5:1 | passa |
| `ink_soft` #33565C | `bg` #FFFBFA | 7.78:1 | 4.5:1 | passa |
| `ink_mute` #5A7A80 | `bg` #FFFBFA | 4.51:1 | 4.5:1 | passa |
| `ink` #0B2B33 | `surface` #FFFFFF | 14.92:1 | 4.5:1 | passa |
| `ink` #0B2B33 | `surface_alt` #EAF6F5 | 13.50:1 | 4.5:1 | passa |
| `on_primary` #0B2B33 | `primary` #00BD9D | 6.23:1 | 4.5:1 | passa |
| `on_primary` #0B2B33 | `primary_hover` #00A88C | 4.96:1 | 4.5:1 | passa |
| `on_primary` #0B2B33 | `primary_press` #00A489 | 4.74:1 | 4.5:1 | passa |
| `ink` #0B2B33 | `accent` #49C6E5 | 7.45:1 | 4.5:1 | passa |
| `ink` #0B2B33 | `accent_soft` #8BD7D2 | 9.06:1 | 4.5:1 | passa |
| `success_text` #00785F | `bg` #FFFBFA | 5.30:1 | 4.5:1 | passa |
| `warning_text` #A15C00 | `bg` #FFFBFA | 5.05:1 | 4.5:1 | passa |
| `danger_text` #B3261E | `bg` #FFFBFA | 6.36:1 | 4.5:1 | passa |
| `focus` #0E6A80 | `bg` #FFFBFA | 6.02:1 | 3.0:1 | passa |

Duas observacoes sobre a tabela:

- **`ink_mute` esta em 4.51:1**, ou seja, a um centesimo do piso. Ele e o
  limite absoluto de clareamento do texto secundario. Clarear mais reprova.
- **`focus` usa 3.0:1 e nao 4.5:1** porque o anel de foco e um elemento
  nao textual, e a norma cobra 3:1 para esses. Sky Aqua puro daria 1.95:1
  e por isso nao serve como anel; a versao profunda `#0E6A80` da 6.02:1.

## 3. Estado nunca depende so de cor

Daltonismo tira a cor da mesa como canal unico de informacao. Cada estado
da fila carrega tres canais ao mesmo tempo:

| Estado | Icone | Texto | Cor |
|---|---|---|---|
| Aguardando | ampulheta | "Aguardando" | `ink_mute` |
| Convertendo | repetir | "Convertendo" | `ink_soft` |
| Concluido | check | "Concluido" | `success_text` |
| Falhou | alerta | "Falhou" mais a mensagem | `danger_text` |
| Cancelado | x | "Cancelado" | `ink_mute` |

`tests/test_queue_row.py` verifica isso para **todos** os membros do enum
`Estado`, com `parametrize` sobre `list(Estado)`. Um estado novo que
alguem acrescente sem icone e sem rotulo quebra o teste automaticamente.

## 4. Alvo de clique e teclado

- Todo botao tem no minimo **32 por 32 pixels**, verificado por teste em
  `test_alvo_de_clique_minimo`, presente na linha da fila e na barra de
  destino.
- Todo botao que mostra so icone tem `accessibleName` preenchido, tambem
  verificado por teste. O nome inclui o nome do arquivo, por exemplo
  "Remover da fila: relatorio.pdf", para que um leitor de tela diga qual
  item a acao afeta.
- O botao de acao da linha e **um so, que troca de papel**, em vez de tres
  botoes aparecendo e sumindo. Isso mantem a posicao do alvo estavel
  enquanto o item muda de estado, o que importa para quem tem dificuldade
  motora.
- A zona de arraste responde a Enter e Espaco, alem do clique, e tem
  `StrongFocus`, entao ela e alcancavel por Tab.

## 5. Movimento

A transicao da zona de arraste entre o tamanho grande e a faixa fina dura
250 ms. Quando o sistema indica preferencia por menos movimento, o valor
final e aplicado direto, sem animar. A consulta e defensiva porque o Qt
nao expoe essa preferencia de forma estavel entre versoes: se a versao
instalada nao souber responder, o padrao e animar.

## 6. Navegacao por teclado, verificada por teste

`tests/test_roteiro.py` percorre a cadeia de foco da janela real com
`focusNextChild`, comeca na zona de arraste e da a volta completa. Ele
coleta todos os botoes visiveis e habilitados e falha nomeando qualquer um
que o Tab nao alcance. Com um item na fila, a cobertura inclui os botoes
da linha, que sao os que aparecem e somem conforme o estado.

Dois testes cuidam do lado visual e do acionamento:

- a folha de estilo precisa definir estado `:focus` e usar o token `focus`;
- a zona de arraste precisa responder a Enter, Return e Espaco, para que
  quem chega nela por Tab consiga abrir o seletor de arquivos sem mouse.

## 7. O que ainda nao foi verificado

Honestidade sobre o limite desta auditoria:

- **Foco visivel de fato.** O teste garante que o QSS define o estado e usa
  o token auditado, mas ninguem olhou para a tela para confirmar que o anel
  aparece onde deveria.
- **Leitor de tela real** (Narrator ou NVDA) nao foi testado. Os
  `accessibleName` existem e sao verificados por teste, mas ninguem
  escutou o resultado.
- **Modo de alto contraste do Windows** nao foi avaliado. O app usa QSS
  proprio, que tipicamente ignora o tema de alto contraste do sistema, e
  isso e uma limitacao conhecida e nao resolvida.
