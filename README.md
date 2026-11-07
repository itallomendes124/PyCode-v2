# PyCode v2

Editor de código Python estilo VS Code, feito para tablet e celular Android.
Roda o Python oficial do Termux e funciona sem internet depois de instalado.

> Parte do código foi feita com ajuda de IA (Claude, da Anthropic).

## O que tem

- Explorador de arquivos, abas e vários projetos.
- Erros enquanto você digita: sintaxe, nome não definido, import não usado e módulo não instalado.
- Terminal com `input()`, aba Problemas e botão Parar.
- `tkinter` próprio: as janelas do seu programa aparecem dentro da página.
- Exportar e importar projetos em `.zip`.
- Barra de símbolos para tela de toque.

## APK para Android (teste)

Há uma versão em APK, sem Termux, na aba [Releases](https://github.com/itallomendes124/PyCode-v2/releases).
Ela é gerada automaticamente pelo GitHub a cada atualização do código.
**Ainda é de teste:** executa programas (▶, `input()`, ■ e janelas `tkinter`), mas ainda precisa de testes em aparelho real.
Dá para escolher a pasta dos projetos em Configurações, *Pasta dos projetos*.
O código do app fica na pasta `android/`.

## Requisitos

- Android com **Termux** e **Termux:Widget**. Instale os dois da mesma origem (F-Droid ou GitHub).
- Internet só na instalação, para baixar o editor Ace.

## Instalar no Termux

    pkg install -y git python
    git clone https://github.com/itallomendes124/PyCode-v2.git
    bash PyCode-v2/instalar_termux.sh

Toque em **Permitir** quando o Android pedir acesso aos arquivos.
Espere aparecer `Pronto!`.

Depois crie o ícone: segure a tela inicial, toque em **Widgets**, depois **Termux:Widget**, **Termux shortcut** e **PyCode**.

Deixe a bateria do Termux em **Sem restrições** (Configurações, Apps, Termux, Bateria).

## Usar

Toque no ícone. O Chrome abre o PyCode em `http://127.0.0.1:8765/`.

Sem o ícone:

    bash ~/.shortcuts/PyCode

Seus projetos ficam em `Armazenamento interno/PyCode/projetos`.

Parar o servidor:

    pkill -f "pycode_[s]ervidor"

Se algo falhar:

    bash ~/PyCode-app/termux/diagnostico.sh

## Atualizar

    cd ~/PyCode-v2 && git pull && bash instalar_termux.sh

Seus projetos não são apagados.

## No computador (Windows, Linux, macOS)

    python pycode_servidor.py

No Windows, para criar um atalho na área de trabalho:

    python pycode_servidor.py --instalar

## Estrutura

    PyCode-v2/
    ├── pycode_servidor.py     servidor local (só biblioteca padrão)
    ├── PyCode.pyw             abre em janela de app (Windows)
    ├── instalar_termux.sh     instalador do Termux
    ├── termux/
    │   ├── PyCode             script do ícone (liga o servidor e abre o Chrome)
    │   └── diagnostico.sh     mostra o que está faltando
    ├── ponte/tkinter/         tkinter próprio, desenhado na página
    └── web/                   interface (index.html, ícones, manifest)

## Como funciona

- Um servidor Python local, só com a biblioteca padrão, atende em `127.0.0.1`.
- Ao tocar em ▶, ele roda o seu arquivo como um programa separado. O botão ■ encerra esse programa.
- A interface é uma página com o editor [Ace](https://ace.c9.io/), baixado na instalação.
- O `tkinter` próprio manda comandos de desenho para a página.

## Limites

- Projeto pessoal em evolução. Pode ter bugs.
- O `tkinter` próprio manda comandos de desenho para a página.
- Não tem `pip` embutido e não substitui o VS Code do computador.
- **Segurança:** o servidor não tem senha. Outros apps do mesmo aparelho conseguem acessar `127.0.0.1:8765`. Instale só apps em que você confia.
- O PyCode do Android não tem `pip`, e bibliotecas como NumPy, Pandas e PyTorch não rodam nele (precisam de código nativo compilado para o aparelho). No computador, o PyCode usa o seu Python e o `pip` normal.
- O PyCode não substitui o VS Code do computador.

## Segurança
O PyCode abre um servidor só no seu aparelho (`127.0.0.1`). O que protege os seus projetos:

- **Token por sessão.** Cada vez que o servidor liga, ele sorteia um token novo, e todas as rotas da API (inclusive exportar) exigem esse token. Isso impede que um **site** aberto no navegador leia ou altere seus projetos por esse servidor.
- **Chave de abertura (app Android).** No APK, a própria página só é entregue a quem traz a chave (`?k=`), que só o WebView do app recebe. Assim, outro **app** instalado no aparelho não consegue pegar o token só pedindo a página.
- **Checagem de `Host`** (contra DNS rebinding), validação de nomes de arquivo e de projeto, e limites ao importar `.zip` (número de entradas, tamanho total e taxa de compressão).

**O que continua sem proteção:**

- No **Termux e no computador** a página é aberta pelo navegador e não existe chave de abertura. Outro programa rodando no mesmo aparelho pode pedir a página e pegar o token. Nesses casos o token protege contra sites, não contra programas locais.
- O código Python que você executa roda com as permissões do app. Ele pode ler e apagar os arquivos que o app enxerga. Rode só código em que você confia.

Os detalhes, as provas e os riscos que ficaram estão em `AUDITORIA.md`.

## Testes
Os testes usam só a biblioteca padrão do Python:

    python3 -m unittest discover -s testes -p "test_*.py"

Veja `testes/README.md` para rodar por área.
