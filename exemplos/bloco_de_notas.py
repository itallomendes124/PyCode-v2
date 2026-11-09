"""Bloco de notas: usa tkinter.filedialog (abrir e salvar) e tkinter.font (fonte que muda ao vivo)."""
import tkinter as tk
from tkinter import filedialog, font, messagebox

janela = tk.Tk()
janela.title("Bloco de notas")
janela.geometry("440x460")

fonte = font.Font(family="Courier", size=12)
atual = {"caminho": None}
status = tk.StringVar(value="Arquivo novo")

texto = tk.Text(janela, font=fonte, wrap="word", height=14)


def atualizar_status(evento=None):
    linhas = texto.get("1.0", tk.END).rstrip("\n").split("\n")
    maior = max(linhas, key=len)
    nome = atual["caminho"].rsplit("/", 1)[-1] if atual["caminho"] else "sem nome"
    status.set(f"{nome} | {len(linhas)} linhas | maior linha: {fonte.measure(maior)} px")


def abrir():
    caminho = filedialog.askopenfilename(
        title="Abrir arquivo",
        filetypes=[("Texto", "*.txt *.md *.py"), ("Todos", "*.*")])
    if not caminho:
        return
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            conteudo = arquivo.read()
    except (OSError, UnicodeDecodeError) as erro:
        messagebox.showerror("Não consegui abrir", str(erro))
        return
    texto.delete("1.0", tk.END)
    texto.insert("1.0", conteudo)
    atual["caminho"] = caminho
    atualizar_status()


def gravar(caminho):
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto.get("1.0", tk.END).rstrip("\n") + "\n")
    atual["caminho"] = caminho
    atualizar_status()


def salvar_como():
    caminho = filedialog.asksaveasfilename(
        title="Salvar como", defaultextension=".txt",
        filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
    if caminho:
        gravar(caminho)


def salvar():
    if atual["caminho"]:
        gravar(atual["caminho"])
    else:
        salvar_como()


def mudar_tamanho(valor):
    fonte.configure(size=int(float(valor)))  # a fonte muda em todos os widgets que a usam
    atualizar_status()


def alternar_negrito():
    fonte.configure(weight="normal" if fonte["weight"] == "bold" else "bold")
    atualizar_status()


barra = tk.Menu(janela)
arquivo_menu = tk.Menu(barra, tearoff=0)
arquivo_menu.add_command(label="Abrir...", command=abrir)
arquivo_menu.add_command(label="Salvar", command=salvar)
arquivo_menu.add_command(label="Salvar como...", command=salvar_como)
arquivo_menu.add_separator()
arquivo_menu.add_command(label="Sair", command=janela.destroy)
barra.add_cascade(label="Arquivo", menu=arquivo_menu)
janela.config(menu=barra)

controles = tk.Frame(janela)
controles.pack(fill="x", padx=6, pady=4)
tk.Label(controles, text="Tamanho:").pack(side="left")
tk.Scale(controles, from_=8, to=32, orient="horizontal", command=mudar_tamanho).pack(side="left", fill="x", expand=True)
tk.Button(controles, text="Negrito", command=alternar_negrito).pack(side="left", padx=6)

# o rótulo é empacotado antes, embaixo, para a fonte grande não empurrá-lo para fora da janela
tk.Label(janela, textvariable=status, anchor="w", relief="sunken").pack(side="bottom", fill="x", padx=6, pady=4)
texto.pack(fill="both", expand=True, padx=6)
texto.insert("1.0", "Use o menu Arquivo para abrir ou salvar.\nMexa no tamanho e no negrito.")
texto.bind("<KeyRelease>", atualizar_status)
atualizar_status()

janela.mainloop()
print("fim")
