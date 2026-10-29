# PyCode

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

Há uma versão em APK, sem Termux, na aba [Releases](https://github.com/itallomendes124/pycode/releases).
Ela é gerada automaticamente pelo GitHub a cada atualização do código.
**Ainda é de teste:** executa programas (▶, `input()`, ■ e janelas `tkinter`), mas ainda precisa de testes em aparelho real.
Dá para escolher a pasta dos projetos em Configurações, *Pasta dos projetos*.
O código do app fica na pasta `android/`.

## Requisitos

- Android com **Termux** e **Termux:Widget**. Instale os dois da mesma origem (F-Droid ou GitHub).
- Internet só na instalação, para baixar o editor Ace.

## Instalar no Termux

    pkg install -y git python
    git clone https://github.com/itallomendes124/pycode.git
    bash pycode/instalar_termux.sh

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

    cd ~/pycode && git pull && bash instalar_termux.sh

Seus projetos não são apagados.

## No computador (Windows, Linux, macOS)

    python pycode_servidor.py

No Windows, para criar um atalho na área de trabalho:

    python pycode_servidor.py --instalar

## Estrutura

    pycode/
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
- O `tkinter` cobre a maior parte do uso comum: `Label`, `Button`, `Entry`, `Text`, `Canvas`, `Frame`, `Listbox`, `Checkbutton`, `Radiobutton`, `Scale`, `Spinbox`, `Menu`, `PhotoImage` (PNG, GIF, JPEG) e, do `ttk`, `Combobox` e `Notebook`. Ainda não cobre tudo do tkinter oficial (por exemplo `Treeview`, `Canvas` com formas avançadas e temas do `ttk`).
- Não tem `pip` embutido e não substitui o VS Code do computador.
- **Segurança:** o servidor não tem senha. Outros apps do mesmo aparelho conseguem acessar `127.0.0.1:8765`. Instale só apps em que você confia.
