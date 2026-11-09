# Auditoria de segurança do PyCode v2

Este documento diz o que foi encontrado, como foi comprovado, o que foi corrigido, o que **não** foi
corrigido e o que **não** foi testado. Onde algo não foi verificado, está escrito.

## Resumo

- Foram encontradas **4 falhas de segurança** no servidor local (uma delas só corrigida no APK), **2 melhorias de robustez** e **1 defeito de confiabilidade** (o botão preso em ■, item A7). Todos os corrigidos têm teste.
- **179 testes automatizados** passam (`testes/resultado.txt` guarda a execução).
- Os testes de segurança e do botão de executar foram conferidos **estragando o código de propósito**: com o defeito de volta, eles falham.
- **Não foi testado em aparelho Android real.** Veja "O que não foi testado".
- Durante o trabalho, o pacote `pycode-widgets.zip` desfez duas correções anteriores (botão de executar e nomes do PyCode v2). Foi corrigido e há teste de regressão. Veja o item R0.

## Como o PyCode está montado (resumo)

- `pycode_servidor.py`: servidor HTTP em `127.0.0.1` (API, arquivos estáticos, projetos, exportar e importar).
- `web/index.html`: o editor, que fala com a API.
- `ponte/tkinter/`: o `tkinter` do PyCode (desenha as janelas na página, porque o Android não tem Tcl/Tk).
- `android/`: app com Chaquopy (CPython 3.13 oficial), WebView e um serviço `:executor` que roda o programa do usuário em processo separado.

O Python do app é o CPython oficial. **A única biblioteca padrão substituída é o `tkinter`**, e isso é inevitável no Android.

## Achados

| ID | Gravidade | Onde | Problema | Como foi comprovado | Correção | Testes |
|---|---|---|---|---|---|---|
| A1 | Alta | `pycode_servidor.py`, GET `/api/exportar` | A rota respondia **antes** de checar o cabeçalho de acesso. Qualquer cliente local baixava o `.zip` de um projeto. | Pedido sem cabeçalho devolveu `200` e um `.zip`. | Exportar passa pela mesma autenticação das outras rotas. O link de download da página leva o token em `?tk=`. | `test_exportar_sem_token_bloqueado`, `test_exportar_com_tk_errado_bloqueado`, `test_exportar_pelo_botao_da_pagina_funciona_com_token` |
| A2 | Alta | todas as rotas `/api/` | O "acesso" era o cabeçalho fixo `X-PyCode: 1`, que qualquer programa conhece. | Qualquer pedido com `X-PyCode: 1` passava. | Token por sessão (`secrets.token_urlsafe(24)`), comparado em tempo constante. O valor `1` deixou de valer. | `test_cabecalho_fixo_1_nao_vale_mais`, `test_rota_com_token_errado_bloqueada` |
| A3 | Média | `pycode_servidor.py`, GET `/` | A página, com o token dentro, era entregue a **qualquer cliente local**. Um app mal-intencionado pedia `/`, lia o token e acessava a API. (O token sozinho só protege contra **sites**.) | Pedido a `/` devolveu o token, e com ele `/api/projetos` respondeu `200`. | **APK:** a página só é entregue com a chave `?k=`, que só o WebView recebe (`MainActivity.abrirEditor`). **Termux e computador: não corrigido** (veja R1). | `TestChaveDeAbertura` (7 testes) e a simulação do caminho do APK |
| A4 | Média | `pycode_servidor.py`, importar `.zip` | Sem limite de entradas, de tamanho nem de compressão. | Um `.zip` com 20.001 entradas foi aceito e 20.000 arquivos foram gravados. | Limites: 500 entradas, 20 MB descompactados, razão de compressão 200:1. | `test_zip_com_muitas_entradas_rejeitado`, `test_zip_bomb_por_razao_rejeitado` |
| A5 | Baixa | comparação do token | `hmac.compare_digest` com texto fora do ASCII gerava erro `500` em vez de `403`. | Leitura do código e teste. | A comparação passou a usar bytes. | `test_texto_fora_do_ascii_da_403_e_nao_500` |
| A6 | Baixa | servidor | Quando o navegador fechava a conexão, o servidor despejava um erro enorme no log. | Visto nos logs dos testes. | Só erros de conexão são ignorados. Qualquer outro erro continua aparecendo. | `TestErrosDeConexao` (2 testes) |
| A7 | Média (confiabilidade) | `android/.../pycode_runner.py`, `_esperar_threads` | O executor esperava **todas** as threads não-daemon antes de avisar o "fim". No Android ele roda numa thread do Java e a **thread principal do Python fica viva para sempre**; ele esperava por ela e nunca avisava. O programa terminava, mas o app ficava em ■ sem "Finalizado". | Visto no tablet (programa de diagnóstico: relatório na tela, ■ preso, sem "Finalizado"). Reproduzido aqui rodando o executor numa thread secundária com a principal viva: os 4 testes novos falharam com o fim `None`. | A espera ignora a thread principal e as que já existiam antes do programa. Threads **do usuário** continuam sendo esperadas, como no Python normal. | `TestComoNoAndroid` (4 testes) |

## Verificado e sem problema (com teste)

- **DNS rebinding:** pedido com `Host` diferente de `127.0.0.1`/`localhost` recebe `403`.
- **Traversal em nomes:** `../`, `..%2f`, caminhos absolutos e barras em nome de arquivo ou de projeto são recusados.
- **Traversal dentro do `.zip`:** `../../fora.py` vira só `fora.py` dentro do projeto. Nada sai da pasta.
- **Rotas e métodos desconhecidos:** devolvem `404`, sem expor caminhos internos nem rastros de erro.
- **JSON malformado:** `400`. **Arquivo maior que o limite:** recusado. **Extensão não permitida:** recusada.
- **Parar um programa:** `SIGKILL` no processo; laço infinito encerra de verdade e **não sobra processo órfão**.
- **Executor:** recusa conexão sem o token próprio dele. A saída do programa é limitada.
- **Sem CORS:** o servidor não manda `Access-Control-Allow-Origin`, então um site não consegue ler as respostas.
- **Android (leitura do código):** `allowBackup="false"`; o serviço do executor tem `exported="false"`; o WebView não acessa `file://` nem conteúdo; links externos abrem fora do app; a única função exposta ao JavaScript é `escolherPasta` (abre o seletor de pasta).
- **Calculadora de exemplo:** o avaliador usa `ast`, não `eval`, e recusa `__import__`, `open`, `lambda`, atributos e expoentes gigantes.

## Rota acrescentada na Fase C: `/api/pasta`

O `tkinter.filedialog` do PyCode abre um seletor próprio, e ele precisa listar pastas. A rota foi desenhada para listar o mínimo:

- **Exige o token**, como as demais rotas.
- **Só lista dentro de duas raízes:** a pasta dos projetos e, no Android, `/storage/emulated/0`. O caminho é resolvido (`..` e links simbólicos) antes de comparar, então `../../` e atalhos que apontam para fora recebem `403`.
- **Devolve só nomes, tipo e tamanho.** Nunca o conteúdo de um arquivo. Arquivos que começam com ponto não aparecem, e a lista para em 2.000 itens.
- Os 9 testes de `TestListarPasta` cobrem token, `..`, link simbólico, pasta inexistente, limite e que nada de conteúdo vaza. Tirei a checagem de pasta permitida de propósito, e 3 testes falharam.
- **Risco residual:** o app passa a poder mostrar *os nomes* dos arquivos do armazenamento compartilhado a quem tem o token. Quem já tem o token e roda código no app já podia ler esses arquivos pelo `open()`, então não é um poder novo, mas é uma superfície nova.

## Regressões que eu causei (R0)

O pacote `pycode-widgets.zip` sobrescreveu `web/index.html` e `README.md` com cópias antigas. Resultado no GitHub:
- o botão de executar **voltou a não devolver o ▶ na hora** ao tocar no ■;
- o README **voltou aos nomes antigos** (`# PyCode`, `pycode.git`).

Na Fase C achei outro erro meu, no README: a seção "Limites" tinha perdido a linha com a cobertura do `tkinter`, ganhado uma frase repetida e mantido uma linha antiga e falsa ("o servidor não tem senha"). Foi reescrita, e `test_documentos.py` agora confere o README contra o código.

O botão preso tinha **outra causa, mais profunda** (A7), que as correções anteriores (servidor e página) não tocavam. Eu as fiz sem conseguir reproduzir o defeito, e o teste no tablet mostrou que não bastavam. A causa real só apareceu quando o executor passou a ser testado do jeito que o Android o roda (numa thread secundária).

Corrigido neste pacote. O teste `test_botao_volta_na_hora_ao_tocar_em_parar` bloqueia o pedido de parar no navegador, então **só a correção da página** consegue devolver o botão. Conferi estragando a página: o teste falha (`'Parar' != 'Executar'`).

## Riscos que continuam

| ID | Risco | O que seria preciso |
|---|---|---|
| R1 | **Termux e computador:** a página (com o token) é entregue a qualquer programa local que a peça. O token protege contra sites, não contra programas. | O servidor gravar a chave em arquivo privado e o atalho abrir a URL com `?k=`. Exige mudar os scripts do Termux e validar com o app instalado. |
| R2 | **Sem sandbox:** o código do usuário roda com as permissões do app. Com "Acesso a todos os arquivos" ligado, pode ler e apagar a pasta escolhida e outras áreas. | Não rodar código não confiável. A alternativa técnica (Storage Access Framework) é uma mudança grande. |
| R3 | **Sem limite de CPU, memória e tempo** no executor. O ■ encerra o processo, e a saída é limitada, mas um programa pode consumir CPU até você parar. | `RLIMIT_AS` não foi usado porque o processo do executor hospeda a JVM e quebraria. Um tempo máximo padrão mataria programas de janela. Seria preciso um limite configurável por execução. |
| R4 | A permissão `MANAGE_EXTERNAL_STORAGE` é ampla. Ela existe para você escolher a pasta dos projetos fora do app. | Trocar por Storage Access Framework. |
| R5 | A **chave de assinatura de depuração é pública** no repositório (`debug.keystore`). Qualquer pessoa pode assinar um APK com a mesma chave. Serve só para o APK de teste. | Para distribuir: gerar chave própria, guardar nos segredos do GitHub e nunca no repositório. |
| R6 | As ações do GitHub (`checkout@v4` etc.) estão fixadas por versão, não por hash. O GitHub avisa que o Node 20 será descontinuado. | Fixar por hash exige conferir os hashes com internet. |
| R7 | O token vai na URL do link de exportar (`?tk=`) e pode ficar no histórico do WebView. É um token de sessão, mas é uma exposição. | Trocar o download por uma requisição com cabeçalho. |
| R8 | A mudança em `MainActivity.java` **não foi compilada aqui** (sem Android SDK). Só a compilação do GitHub Actions confirma. | Rodar o workflow e instalar o APK. |

## Testes

Execução em Linux, Python 3.12, com o executor e o Chromium simulando o caminho do APK.

| Arquivo | Testes | Cobre |
|---|---|---|
| `test_api_seguranca.py` | 27 | token, chave de abertura, exportar, `Host`, métodos, erros, erros de conexão |
| `test_projetos_arquivos.py` | 22 | projetos, arquivos, traversal, limites, `.zip`, e a rota `/api/pasta` do seletor de arquivos |
| `test_executor.py` | 16 | saída, `input()`, erros, parar, órfãos, saída limitada, fim do programa como no Android |
| `test_tkinter.py` | 11 | widgets básicos, variáveis, layout, eventos |
| `test_tkinter_fontes_arquivos.py` | 28 | `tkinter.font` e `tkinter.filedialog`, inclusive pela ponte real do executor |
| `test_tkinter_widgets.py` | 21 | Checkbutton, Radiobutton, Scale, Spinbox, Combobox, Notebook, Menu, PhotoImage |
| `test_calculadora.py` | 11 | contas, conversor, segurança do avaliador |
| `test_build.py` | 19 | o build normal não muda: `pip` e identificador novo só existem na variante com bibliotecas |
| `test_documentos.py` | 8 | o README e as notas não prometem nem negam o que o código não faz |
| `test_navegador.py` | 16 | página real: token, botão ▶/■, janela `tkinter`, exportar, widgets, seletor de arquivos, fontes, empacotamento |
| **Total** | **179** | **todos passam** |

Para rodar: `python3 -m unittest discover -s testes -p "test_*.py"`. Veja `testes/README.md`.

### Conferência por sabotagem

Estraguei o código de propósito e conferi se os testes reclamam:

| Defeito reintroduzido | Resultado |
|---|---|
| `Checkbutton.select()` deixa de marcar | falha (2 testes) |
| avaliador da calculadora aceita qualquer nome | falha (3 testes) |
| `/api/exportar` volta a ficar sem token | falha (2 testes) |
| página entregue sem chave de abertura | falha (4 testes) |
| comparação do token volta a usar texto | falha (1 teste) |
| `parar()` da página volta à versão antiga | falha (`'Parar' != 'Executar'`) |
| `_esperar_threads` volta a esperar a thread principal | falha (4 testes, fim `None`) |
| a rota `/api/pasta` deixa de checar a pasta permitida | falha (3 testes) |
| a ponte deixa de esperar a resposta do seletor de arquivos | falha (teste da ponte real) |
| `Font` deixa de ser entendida pela serialização | falha |
| a página responde ao Python sem esperar a Promise | falha (o seletor fecha sozinho) |
| o README volta a ter linha repetida e o texto antigo sobre senha | falha (2 testes) |
| peças com `expand` voltam a não encolher | falha (rodapé sai da janela) |

Um dos testes do botão passou mesmo com o defeito de volta. Eu o reescrevi até ele falhar. Por isso a conferência existe.

## O que não foi testado

- **Aparelho Android real.** Tudo foi simulado em Linux. O WebView do Android pode se comportar diferente do Chromium.
- **A compilação do APK com a mudança em `MainActivity.java`** (R8).
- **Windows e macOS.** Só Linux.
- **Python 3.13 do Chaquopy.** Os testes rodaram em 3.12.
- **A caixa "Sobre" e o toque nos menus** no tablet.
- **Desempenho e rotação de tela.**

## Próximos passos recomendados

1. Instalar o APK novo e rodar `exemplos/calculadora.py`.
2. Resolver R1 (chave de abertura no Termux e no computador).
3. Se o PyCode for distribuído a outras pessoas: R5 (chave própria) e R2 (aviso claro de que o código roda sem isolamento).
