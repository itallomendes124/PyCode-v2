# Testes do PyCode

Usam só a biblioteca padrão (`unittest`). Nada para instalar.

## Rodar tudo

    python3 -m unittest discover -s testes -p "test_*.py"

## Rodar por área

    python3 -m unittest testes.test_api_seguranca
    python3 -m unittest testes.test_projetos_arquivos
    python3 -m unittest testes.test_executor
    python3 -m unittest testes.test_tkinter
    python3 -m unittest testes.test_tkinter_widgets
    python3 -m unittest testes.test_calculadora
    python3 -m unittest testes.test_build
    python3 -m unittest testes.test_tkinter_fontes_arquivos
    python3 -m unittest testes.test_documentos
    python3 -m unittest testes.test_eventos
    python3 -m unittest testes.test_navegador     # precisa do Playwright; pula sozinho sem ele

## O que cada arquivo cobre

| Arquivo | O que verifica |
|---|---|
| `test_api_seguranca.py` | token por sessão, exportar protegido, checagem de `Host`, rotas e métodos, erros sem vazar caminho |
| `test_projetos_arquivos.py` | criar, listar, salvar, renomear, excluir; traversal; limites; importar `.zip` (zip bomb, entradas demais, `../` dentro do zip) |
| `test_executor.py` | saída, `input()`, erros com linha, parar laço infinito de verdade, nenhum processo órfão, saída limitada, executor recusa conexão sem token |
| `test_tkinter.py` | widgets básicos, variáveis, `grid`/`pack`/`place`, `bind`, `after`, `Toplevel`, `Canvas` |
| `test_tkinter_widgets.py` | `Checkbutton`, `Radiobutton`, `Scale`, `Spinbox`, `Combobox`, `Notebook`, `Menu`, `PhotoImage` |
| `test_calculadora.py` | `exemplos/calculadora.py`: contas, conversor e, principalmente, que o avaliador recusa código que não seja conta |
| `test_tkinter_fontes_arquivos.py` | `tkinter.font` (`Font`, `measure`, `metrics`, fontes nomeadas) e `tkinter.filedialog` (abrir, salvar, pasta), inclusive pela ponte real |
| `test_eventos.py` | junção de eventos contínuos pela ponte real (Scale, campo, mouse) e a garantia de que cliques, teclas e escolhas nunca são descartados |
| `test_documentos.py` | o README e as notas conferem com o código: o que diz existir existe, o que diz faltar falta, sem linhas repetidas |
| `test_build.py` | o build normal não muda: o `pip` e o identificador novo só existem na variante com bibliotecas, e os dois workflows não se misturam |
| `test_navegador.py` | página real no Chromium: token, botão de executar voltando a ▶, janela `tkinter`, exportar, widgets novos |

## Como saber se um teste presta

Teste que nunca falha não prova nada. Os testes de segurança e do botão foram conferidos
estragando o código de propósito: com o defeito de volta, eles falham (veja `AUDITORIA.md`).

## Resultado da última execução

`resultado.txt` guarda a saída completa de uma execução real (cada teste e o total).

## O que estes testes não cobrem

O app instalado em um aparelho Android de verdade. Os testes rodam em Linux, com o executor
e o navegador simulando o caminho do APK. Para o aparelho, use o roteiro do `README.md`
(rodar `exemplos/calculadora.py` no app e conferir cada aba).
