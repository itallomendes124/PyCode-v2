import ast
import math
import operator
import struct
import time
import zlib

import tkinter as tk
from tkinter import ttk, messagebox

OPERADORES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Pow: operator.pow}
CONSTANTES = {"pi": math.pi, "e": math.e}
CONFIG = {"graus": True}


def trig(funcao):
    def interna(v):
        return funcao(math.radians(v) if CONFIG["graus"] else v)
    return interna


FUNCOES = {"sqrt": math.sqrt, "sin": trig(math.sin), "cos": trig(math.cos),
           "tan": trig(math.tan), "log": math.log10, "ln": math.log, "abs": abs}

LINHAS = [["C", "⌫", "(", ")", "÷"],
          ["7", "8", "9", "×", "√"],
          ["4", "5", "6", "-", "^"],
          ["1", "2", "3", "+", "sin"],
          ["0", ".", "π", "=", "cos"]]
INSERE = {"√": "sqrt(", "sin": "sin(", "cos": "cos(", "π": "pi"}

FATORES = {"Comprimento": {"m": 1, "km": 1000, "cm": 0.01, "mi": 1609.344},
           "Massa": {"kg": 1, "g": 0.001, "lb": 0.45359237},
           "Temperatura": {"°C": None, "°F": None, "K": None}}


def avaliar(texto, x=None):
    """Calcula a expressão sem usar eval (só números, operadores e funções permitidas)."""
    def calc(no):
        if isinstance(no, ast.Expression):
            return calc(no.body)
        if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
            return no.value
        if isinstance(no, ast.BinOp) and type(no.op) in OPERADORES:
            esq, dire = calc(no.left), calc(no.right)
            if isinstance(no.op, ast.Pow) and abs(dire) > 1000:
                raise ValueError("expoente grande demais")
            return OPERADORES[type(no.op)](esq, dire)
        if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.USub, ast.UAdd)):
            valor = calc(no.operand)
            return -valor if isinstance(no.op, ast.USub) else valor
        if isinstance(no, ast.Name) and no.id in CONSTANTES:
            return CONSTANTES[no.id]
        if isinstance(no, ast.Name) and no.id == "x" and x is not None:
            return x
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) \
                and no.func.id in FUNCOES and len(no.args) == 1:
            return FUNCOES[no.func.id](calc(no.args[0]))
        raise ValueError("expressão inválida")

    limpo = texto.replace("×", "*").replace("÷", "/").replace("^", "**").replace(",", ".")
    return calc(ast.parse(limpo, mode="eval"))


def converter(valor, tipo, de, para):
    if tipo == "Temperatura":
        celsius = {"°C": lambda v: v, "°F": lambda v: (v - 32) * 5 / 9, "K": lambda v: v - 273.15}[de](valor)
        return {"°C": lambda c: c, "°F": lambda c: c * 9 / 5 + 32, "K": lambda c: c + 273.15}[para](celsius)
    return valor * FATORES[tipo][de] / FATORES[tipo][para]


def icone_png(n=32):
    bruto = b"".join(
        b"\x00" + b"".join(bytes((40 + x * 200 // n, 120, 255 - y * 200 // n)) for x in range(n))
        for y in range(n))

    def bloco(tipo, dados):
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(bruto)) + bloco(b"IEND", b""))


def main():
    janela = tk.Tk()
    janela.title("Calculadora PyCode v2")
    janela.geometry("380x620")

    expr = tk.StringVar()
    resultado = tk.StringVar(value="0")
    hora = tk.StringVar()
    status = tk.StringVar(value="Pronto")
    modo = tk.StringVar(value="graus")
    arredondar = tk.IntVar(value=0)
    tamanho = tk.IntVar(value=26)

    # ---------- cálculo ----------
    def formatar(valor):
        if arredondar.get():
            try:
                valor = round(valor, int(casas.get()))
            except ValueError:
                pass
        if isinstance(valor, float) and valor.is_integer() and abs(valor) < 1e15:
            valor = int(valor)
        return str(valor)

    def calcular():
        if not expr.get().strip():
            return
        try:
            texto = formatar(avaliar(expr.get()))
        except ZeroDivisionError:
            resultado.set("Divisão por zero")
            return
        except Exception:
            resultado.set("Expressão inválida")
            return
        resultado.set("= " + texto)
        historico.insert(0, f"{expr.get()} = {texto}")
        print(f"{expr.get()} = {texto}")
        status.set("Cálculo feito")

    def apertar(rotulo):
        if rotulo == "C":
            expr.set("")
            resultado.set("0")
        elif rotulo == "⌫":
            expr.set(expr.get()[:-1])
        elif rotulo == "=":
            calcular()
        else:
            expr.set(expr.get() + INSERE.get(rotulo, rotulo))

    # ---------- menu ----------
    barra = tk.Menu(janela)
    arquivo = tk.Menu(barra, tearoff=0)
    arquivo.add_command(label="Limpar histórico", command=lambda: historico.delete(0, tk.END))
    arquivo.add_separator()
    arquivo.add_command(label="Sair", command=janela.destroy)
    barra.add_cascade(label="Arquivo", menu=arquivo)
    ajuda = tk.Menu(barra, tearoff=0)
    ajuda.add_command(label="Sobre", command=lambda: messagebox.showinfo(
        "Sobre", "Calculadora feita no PyCode v2.\nTestando Menu, abas, Canvas e mais."))
    barra.add_cascade(label="Ajuda", menu=ajuda)
    janela.config(menu=barra)

    # ---------- barra de status e abas ----------
    rodape = tk.Frame(janela)
    rodape.pack(side="bottom", fill="x")
    tk.Label(rodape, textvariable=status, anchor="w").pack(side="left", padx=6)
    tk.Label(rodape, textvariable=hora).pack(side="right", padx=6)

    abas = ttk.Notebook(janela)
    abas.pack(fill="both", expand=True, padx=4, pady=4)
    a1, a2, a3, a4, a5 = (tk.Frame(abas) for _ in range(5))
    for quadro, titulo in ((a1, "Calc"), (a2, "Histórico"), (a3, "Conversor"),
                           (a4, "Gráfico"), (a5, "Opções")):
        abas.add(quadro, text=titulo)

    # ---------- aba 1: calculadora ----------
    visor = tk.Frame(a1, bg="white")
    visor.pack(fill="x", padx=8, pady=8)
    tk.Label(visor, textvariable=expr, anchor="e", bg="white", fg="#666666",
             font=("Arial", 12)).pack(fill="x", padx=6)
    rotulo_res = tk.Label(visor, textvariable=resultado, anchor="e", bg="white", font=("Arial", 26))
    rotulo_res.pack(fill="x", padx=6, pady=4)

    teclado = tk.Frame(a1)
    teclado.pack(fill="both", expand=True, padx=8, pady=4)
    for i, linha in enumerate(LINHAS):
        teclado.rowconfigure(i, weight=1)
        for j, rotulo in enumerate(linha):
            teclado.columnconfigure(j, weight=1)
            tk.Button(teclado, text=rotulo, width=4, height=2,
                      command=lambda r=rotulo: apertar(r)).grid(row=i, column=j, sticky="nsew", padx=2, pady=2)

    # ---------- aba 2: histórico ----------
    historico = tk.Listbox(a2, height=16)
    historico.pack(fill="both", expand=True, padx=8, pady=8)

    def recuperar(evento):
        marcado = historico.curselection()
        if marcado:
            expr.set(historico.get(marcado[0]).split(" = ")[0])
            abas.select(a1)
            status.set("Expressão recuperada")

    historico.bind("<<ListboxSelect>>", recuperar)

    # ---------- aba 3: conversor ----------
    tk.Label(a3, text="Tipo:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    tipo = ttk.Combobox(a3, values=list(FATORES), state="readonly")
    tipo.grid(row=0, column=1, sticky="ew", padx=6)
    tk.Label(a3, text="De:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    de = ttk.Combobox(a3, state="readonly")
    de.grid(row=1, column=1, sticky="ew", padx=6)
    tk.Label(a3, text="Para:").grid(row=2, column=0, sticky="e", padx=6, pady=6)
    para = ttk.Combobox(a3, state="readonly")
    para.grid(row=2, column=1, sticky="ew", padx=6)
    tk.Label(a3, text="Valor:").grid(row=3, column=0, sticky="e", padx=6, pady=6)
    valor = tk.Entry(a3)
    valor.grid(row=3, column=1, sticky="ew", padx=6)
    valor.insert(0, "100")
    saida = tk.StringVar(value="—")
    tk.Label(a3, textvariable=saida, font=("Arial", 20)).grid(row=4, column=0, columnspan=2, pady=16)
    a3.columnconfigure(1, weight=1)

    def converter_agora(evento=None):
        try:
            numero = float(valor.get().replace(",", "."))
            saida.set(f"{converter(numero, tipo.get(), de.get(), para.get()):.6g} {para.get()}")
        except (ValueError, KeyError):
            saida.set("—")

    def trocou_tipo(evento=None):
        unidades = list(FATORES[tipo.get()])
        de.config(values=unidades)
        para.config(values=unidades)
        de.set(unidades[0])
        para.set(unidades[1])
        converter_agora()

    tipo.set("Temperatura")
    tipo.bind("<<ComboboxSelected>>", trocou_tipo)
    de.bind("<<ComboboxSelected>>", converter_agora)
    para.bind("<<ComboboxSelected>>", converter_agora)
    valor.bind("<KeyRelease>", converter_agora)
    trocou_tipo()

    # ---------- aba 4: gráfico ----------
    tk.Label(a4, text="f(x) =  (x de -10 a 10, em radianos)").pack(anchor="w", padx=8)
    funcao = tk.Entry(a4)
    funcao.pack(fill="x", padx=8)
    funcao.insert(0, "sin(x)")
    tela = tk.Canvas(a4, width=340, height=240, bg="white")
    tela.pack(pady=8)

    def desenhar():
        largura, altura = 340, 240
        escala = altura / 6
        tela.delete("all")
        tela.create_line(0, altura / 2, largura, altura / 2, fill="#999999")
        tela.create_line(largura / 2, 0, largura / 2, altura, fill="#999999")
        tela.create_text(largura - 10, altura / 2 - 10, text="x")
        trecho = []

        def fechar_trecho():
            if len(trecho) > 1:
                tela.create_line(*[c for ponto in trecho for c in ponto], fill="#3366cc", width=2)

        guardado = CONFIG["graus"]
        CONFIG["graus"] = False  # o gráfico sempre usa radianos
        try:
            for i in range(221):
                x = -10 + 20 * i / 220
                try:
                    y = float(avaliar(funcao.get(), x))
                    if abs(y) > 3:
                        raise ValueError
                    trecho.append((largura * i / 220, altura / 2 - y * escala))
                except Exception:
                    fechar_trecho()
                    trecho = []
            fechar_trecho()
        finally:
            CONFIG["graus"] = guardado
        status.set("Gráfico desenhado (radianos)")

    tk.Button(a4, text="Desenhar", command=desenhar).pack()
    desenhar()

    # ---------- aba 5: opções ----------
    def mudou_modo():
        CONFIG["graus"] = modo.get() == "graus"
        status.set("Ângulos em " + ("graus" if CONFIG["graus"] else "radianos"))

    tk.Label(a5, text="Ângulos:").pack(anchor="w", padx=8, pady=4)
    tk.Radiobutton(a5, text="Graus", variable=modo, value="graus", command=mudou_modo).pack(anchor="w", padx=20)
    tk.Radiobutton(a5, text="Radianos", variable=modo, value="rad", command=mudou_modo).pack(anchor="w", padx=20)
    tk.Checkbutton(a5, text="Arredondar resultado", variable=arredondar).pack(anchor="w", padx=8, pady=8)
    tk.Label(a5, text="Casas decimais:").pack(anchor="w", padx=8)
    casas = tk.Spinbox(a5, from_=0, to=10, width=5)
    casas.pack(anchor="w", padx=20)
    casas.set("2")
    tk.Label(a5, text="Tamanho do resultado:").pack(anchor="w", padx=8, pady=4)
    tk.Scale(a5, from_=14, to=40, orient="horizontal", variable=tamanho,
             command=lambda v: rotulo_res.config(font=("Arial", int(float(v))))).pack(fill="x", padx=8)
    imagem = tk.PhotoImage(data=icone_png())
    tk.Label(a5, image=imagem).pack(pady=12)
    tk.Label(a5, text="Ícone gerado pelo próprio programa").pack()

    # ---------- teclado físico e relógio ----------
    def tecla(e):
        if abas.index(abas.select()) != 0:
            return
        if e.keysym == "Return":
            calcular()
        elif e.keysym == "BackSpace":
            apertar("⌫")
        elif e.keysym == "Escape":
            apertar("C")
        elif e.char and e.char in "0123456789.+-()^":
            apertar(e.char)
        elif e.char == "*":
            apertar("×")
        elif e.char == "/":
            apertar("÷")

    janela.bind("<Key>", tecla)

    def relogio():
        hora.set(time.strftime("%H:%M:%S"))
        janela.after(1000, relogio)

    relogio()
    return janela


main().mainloop()
print("Calculadora encerrada.")
