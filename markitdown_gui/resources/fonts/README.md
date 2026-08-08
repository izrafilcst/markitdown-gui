# Fontes embarcadas

Esta pasta é opcional e hoje está vazia de propósito.

`theme.carregar_fontes()` varre este diretório por `.ttf` e `.otf` e registra
cada arquivo em `QFontDatabase`. Se a pasta estiver vazia, a função não faz
nada e `theme.familia("ui")` cai na cadeia de fallback declarada em
`theme.FONT`, que no Windows resolve para Segoe UI.

## Se você quiser embarcar as fontes de verdade

Coloque aqui os arquivos e nada mais precisa mudar no código:

| Papel | Família | Onde obter | Licença |
|---|---|---|---|
| `ui` | Inter | github.com/rsms/inter | SIL Open Font License 1.1 |
| `mono` | JetBrains Mono | github.com/JetBrains/JetBrainsMono | SIL Open Font License 1.1 |

Baixe manualmente e copie os arquivos para cá. O app não busca nada na rede,
nem no primeiro uso, e essa promessa é verificada por `tests/test_offline.py`.

Use os pesos Regular, Medium e SemiBold. Os demais pesos só aumentam o
tamanho do executável sem aparecer na interface, porque o QSS usa apenas
`font-weight` 500 e 600.

Guarde o arquivo de licença de cada família junto com os `.ttf`, porque a
SIL Open Font License exige que ela acompanhe a redistribuição, e o `.exe`
gerado pelo WP-10 é uma redistribuição.
