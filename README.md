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

### Variante com bibliotecas (teste)
Existe um segundo APK, **PyCode v2 Bib**, com **NumPy 1.26.2, Pandas 2.1.3, Matplotlib 3.8.4 e Pillow 11.0.0**.
Ele instala ao lado do PyCode normal (outro identificador) e não o substitui.
Para gerar: na aba **Actions** do GitHub, escolha **APK Android (com bibliotecas)** e toque em **Run workflow**.
O arquivo sai na release `apk-bibliotecas`, com o nome `PYcodeteste-bibliotecas-AAAA-MM-DD.apk`.
Para testar, rode `exemplos/teste_bibliotecas.py` dentro do app.
O Matplotlib não tem janela no Android: use `matplotlib.use("Agg")` e grave o gráfico em PNG.

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
- Quando o programa demora, os eventos contínuos seguidos (arrastar um `Scale`, digitar num campo, mover o mouse) são juntados e só o último é entregue, como no Tk. Cliques, teclas e mudanças de escolha nunca são descartados.
- Perguntar algo à página (por exemplo `font.measure`) custa uma ida e volta de uns 70 ms; a mesma pergunta repetida usa a resposta guardada. Evite perguntar a cada tecla.

## Limites

- Projeto pessoal em evolução. Pode ter bugs.
- O `tkinter` do PyCode é próprio e cobre a maior parte do uso comum: `Label`, `Button`, `Entry`, `Text`, `Canvas`, `Frame`, `Listbox`, `Checkbutton`, `Radiobutton`, `Scale`, `Spinbox`, `Menu`, `PhotoImage` (PNG, GIF, JPEG), `ttk.Combobox`, `ttk.Notebook`, `tkinter.font` e `tkinter.filedialog`.
- Ainda não existem: `Treeview`, `Progressbar`, `PanedWindow`, `tkinter.colorchooser`, `tkinter.scrolledtext` e `turtle`.
- O `filedialog` do PyCode abre um seletor próprio, que só mostra as pastas dos projetos e o armazenamento do aparelho. Ele devolve caminhos de verdade, que o `open()` consegue abrir. O seletor nativo do Android não serviria, porque devolve um endereço `content://`.
- A lista de `font.families()` é fixa: tem os nomes que a página reconhece, e o resultado visual depende das fontes do aparelho.
- No Android não há `pip` nem Python filho. Bibliotecas nativas (NumPy, Pandas, Matplotlib, Pillow) só entram na compilação do APK, na variante com bibliotecas. SciPy, scikit-learn, PyTorch e TensorFlow não existem para o Python 3.13 do Chaquopy.
- O PyCode não substitui o VS Code do computador.
- Segurança: veja a seção abaixo.

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
