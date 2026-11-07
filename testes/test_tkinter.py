"""Compatibilidade do tkinter próprio.

Carrega a ponte com um TK falso que registra os comandos enviados à página,
sem navegador. Verifica a API Python (o que o programa do usuário chama), não
o desenho em si — esse é coberto pelos testes de navegador, à parte.
"""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PONTE = RAIZ / "ponte" / "tkinter" / "__init__.py"


class TKFalso:
    def __init__(self):
        self.chamadas = []

    def __getattr__(self, nome):
        def registra(*args):
            self.chamadas.append((nome, args))
            return {"medida": 0, "abertas": 1}.get(nome, None)
        return registra


def carregar_tk():
    browser = types.ModuleType("browser")
    browser.window = types.SimpleNamespace(TK=TKFalso())
    sys.modules["browser"] = browser
    spec = importlib.util.spec_from_file_location("tk_ponte", PONTE)
    tk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tk)
    return tk, browser.window.TK


class TestWidgets(unittest.TestCase):
    def setUp(self):
        self.tk, self.TK = carregar_tk()

    def test_cria_janela_e_widgets(self):
        tk = self.tk
        raiz = tk.Tk()
        tk.Label(raiz, text="oi")
        tk.Button(raiz, text="ok")
        tk.Entry(raiz)
        tk.Frame(raiz)
        tipos = [c[1][1] for c in self.TK.chamadas if c[0] == "criar"]
        for esperado in ("label", "button", "entry", "frame"):
            self.assertIn(esperado, tipos)

    def test_stringvar_liga_no_label(self):
        tk = self.tk
        raiz = tk.Tk()
        v = tk.StringVar(value="a")
        tk.Label(raiz, textvariable=v)
        v.set("b")
        self.assertEqual(v.get(), "b")

    def test_intvar_converte(self):
        tk = self.tk
        tk.Tk()
        v = tk.IntVar(value=5)
        self.assertEqual(v.get(), 5)
        v.set(9)
        self.assertEqual(v.get(), 9)

    def test_entry_get_insert_delete(self):
        tk = self.tk
        raiz = tk.Tk()
        e = tk.Entry(raiz)
        e.insert(0, "abc")
        self.assertEqual(e.get(), "abc")
        e.delete(0, tk.END)
        self.assertEqual(e.get(), "")

    def test_listbox_insert_get_delete_selection(self):
        tk = self.tk
        raiz = tk.Tk()
        lb = tk.Listbox(raiz)
        lb.insert(tk.END, "um", "dois", "tres")
        self.assertEqual(lb.size(), 3)
        self.assertEqual(lb.get(0), "um")
        self.assertEqual(lb.get(0, tk.END), ("um", "dois", "tres"))
        lb.delete(1)
        self.assertEqual(lb.get(0, tk.END), ("um", "tres"))

    def test_grid_pack_place_nao_quebram(self):
        tk = self.tk
        raiz = tk.Tk()
        tk.Label(raiz, text="g").grid(row=0, column=0, sticky="nsew")
        tk.Label(raiz, text="p").pack(side="top", fill="x")
        tk.Label(raiz, text="l").place(x=10, y=20)

    def test_bind_e_after(self):
        tk = self.tk
        raiz = tk.Tk()
        raiz.bind("<Key>", lambda e: None)
        cid = raiz.after(100, lambda: None)
        raiz.after_cancel(cid)

    def test_canvas_desenha(self):
        tk = self.tk
        raiz = tk.Tk()
        c = tk.Canvas(raiz, width=100, height=100)
        r = c.create_rectangle(0, 0, 10, 10, fill="red")
        c.move(r, 5, 5)
        self.assertEqual(len(c.coords(r)), 4)

    def test_messagebox_e_simpledialog_existem(self):
        tk = self.tk
        self.assertTrue(hasattr(tk, "messagebox"))
        self.assertTrue(callable(tk.messagebox.showinfo))
        self.assertTrue(callable(tk.simpledialog.askstring))

    def test_toplevel_varias_janelas(self):
        tk = self.tk
        raiz = tk.Tk()
        top = tk.Toplevel(raiz)
        top.title("segunda")
        janelas = [c for c in self.TK.chamadas if c[0] == "novaJanela"]
        self.assertGreaterEqual(len(janelas), 2)

    def test_fechar_janela_protocolo(self):
        tk = self.tk
        raiz = tk.Tk()
        chamou = []
        raiz.protocol("WM_DELETE_WINDOW", lambda: chamou.append(1))
        raiz.destroy()


if __name__ == "__main__":
    unittest.main()
