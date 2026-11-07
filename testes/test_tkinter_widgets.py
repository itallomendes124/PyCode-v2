"""API dos widgets adicionados ao tkinter próprio.

Usa o mesmo TK falso de test_tkinter.py: confere o que o programa do usuário
enxerga (variáveis, valores, callbacks). O desenho no navegador é coberto por
test_navegador.py.
"""
import base64
import os
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_tkinter import carregar_tk  # noqa: E402


def png_minimo():
    bruto = b"\x00" + bytes((200, 30, 30)) * 2
    bruto = bruto * 2

    def bloco(tipo, dados):
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(bruto)) + bloco(b"IEND", b""))


class Base(unittest.TestCase):
    def setUp(self):
        self.tk, self.TK = carregar_tk()
        self.raiz = self.tk.Tk()


class TestCheckERadio(Base):
    def test_checkbutton_select_deselect_toggle(self):
        v = self.tk.IntVar()
        c = self.tk.Checkbutton(self.raiz, text="x", variable=v)
        c.select()
        self.assertEqual(v.get(), 1)
        c.deselect()
        self.assertEqual(v.get(), 0)
        c.toggle()
        self.assertEqual(v.get(), 1)

    def test_checkbutton_onvalue_offvalue(self):
        v = self.tk.StringVar(value="nao")
        c = self.tk.Checkbutton(self.raiz, variable=v, onvalue="sim", offvalue="nao")
        c.select()
        self.assertEqual(v.get(), "sim")
        c.deselect()
        self.assertEqual(v.get(), "nao")

    def test_checkbutton_clique_chama_command_e_atualiza_variavel(self):
        chamadas = []
        v = self.tk.IntVar()
        c = self.tk.Checkbutton(self.raiz, variable=v, command=lambda: chamadas.append(v.get()))
        c._mudou({"valor": "1"})
        self.assertEqual(v.get(), 1)
        self.assertEqual(chamadas, [1])

    def test_radiobuttons_dividem_a_variavel(self):
        cor = self.tk.StringVar(value="a")
        r1 = self.tk.Radiobutton(self.raiz, variable=cor, value="a")
        r2 = self.tk.Radiobutton(self.raiz, variable=cor, value="b")
        r2.select()
        self.assertEqual(cor.get(), "b")
        r1._mudou({"valor": "1"})
        self.assertEqual(cor.get(), "a")


class TestEscalaESpinbox(Base):
    def test_scale_le_valor_inicial_da_variavel(self):
        v = self.tk.IntVar(value=5)
        self.assertEqual(self.tk.Scale(self.raiz, from_=0, to=10, variable=v).get(), 5)

    def test_scale_set_atualiza_variavel(self):
        v = self.tk.IntVar()
        s = self.tk.Scale(self.raiz, from_=0, to=10, variable=v)
        s.set(8)
        self.assertEqual(v.get(), 8)

    def test_scale_command_recebe_o_valor(self):
        recebidos = []
        s = self.tk.Scale(self.raiz, from_=0, to=100, command=recebidos.append)
        s._mudou({"valor": "70"})
        self.assertEqual(recebidos, [70])

    def test_variavel_trace_dispara_quando_o_widget_muda(self):
        avisos = []
        v = self.tk.IntVar()
        v.trace_add("write", lambda *a: avisos.append(v.get()))
        s = self.tk.Scale(self.raiz, from_=0, to=10, variable=v)
        s._mudou({"valor": "4"})
        self.assertEqual(avisos, [4])

    def test_spinbox_set_get_insert_delete(self):
        sp = self.tk.Spinbox(self.raiz, from_=0, to=9)
        sp.set("3")
        self.assertEqual(sp.get(), "3")
        sp.delete(0, self.tk.END)
        self.assertEqual(sp.get(), "")
        sp.insert(0, "7")
        self.assertEqual(sp.get(), "7")


class TestComboENotebook(Base):
    def test_combobox_valores_e_current(self):
        cb = self.tk.ttk.Combobox(self.raiz, values=["x", "y", "z"])
        cb.set("y")
        self.assertEqual(cb.get(), "y")
        self.assertEqual(cb.current(), 1)
        cb.current(2)
        self.assertEqual(cb.get(), "z")

    def test_combobox_config_values_troca_a_lista(self):
        cb = self.tk.ttk.Combobox(self.raiz, values=["a"])
        cb.config(values=["m", "km"])
        cb.set("km")
        self.assertEqual(cb.current(), 1)

    def test_combobox_variavel(self):
        v = self.tk.StringVar(value="b")
        cb = self.tk.ttk.Combobox(self.raiz, textvariable=v, values=["a", "b"])
        self.assertEqual(cb.get(), "b")
        cb._mudou({"valor": "a"})
        self.assertEqual(v.get(), "a")

    def test_notebook_abas_e_indice(self):
        nb = self.tk.ttk.Notebook(self.raiz)
        f1, f2 = self.tk.Frame(nb), self.tk.Frame(nb)
        nb.add(f1, text="A")
        nb.add(f2, text="B")
        self.assertEqual(nb.tabs(), (f1._id, f2._id))
        self.assertEqual(nb.index("end"), 2)
        self.assertEqual(nb.index(nb.select()), 0)
        nb.select(f2)
        self.assertEqual(nb.index(nb.select()), 1)

    def test_notebook_clique_do_usuario_atualiza_a_aba(self):
        nb = self.tk.ttk.Notebook(self.raiz)
        f1, f2 = self.tk.Frame(nb), self.tk.Frame(nb)
        nb.add(f1, text="A")
        nb.add(f2, text="B")
        nb._aba_mudou({"valor": f2._id})
        self.assertEqual(nb.index(nb.select()), 1)


class TestMenuEImagem(Base):
    def test_menu_arvore_com_submenu_e_separador(self):
        barra = self.tk.Menu(self.raiz)
        arq = self.tk.Menu(barra, tearoff=0)
        arq.add_command(label="Abrir", command=lambda: None)
        arq.add_separator()
        arq.add_command(label="Sair", command=lambda: None)
        barra.add_cascade(label="Arquivo", menu=arq)
        arvore = barra._arvore()
        self.assertEqual(arvore[0]["tipo"], "submenu")
        self.assertEqual([i["tipo"] for i in arvore[0]["itens"]], ["comando", "separador", "comando"])
        self.assertEqual(arvore[0]["itens"][0]["label"], "Abrir")
        self.raiz.config(menu=barra)

    def test_menu_delete_remove_itens(self):
        m = self.tk.Menu(self.raiz)
        m.add_command(label="1", command=lambda: None)
        m.add_command(label="2", command=lambda: None)
        m.delete(0, "end")
        self.assertEqual(m._arvore(), [])

    def test_photoimage_de_bytes_vira_data_url(self):
        img = self.tk.PhotoImage(data=png_minimo())
        url = self.tk._imagens[str(img)]
        self.assertTrue(url.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(url.split(",", 1)[1])[:4], b"\x89PNG")

    def test_photoimage_de_arquivo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "a.png")
            with open(caminho, "wb") as arq:
                arq.write(png_minimo())
            img = self.tk.PhotoImage(file=caminho)
            self.assertTrue(self.tk._imagens[str(img)].startswith("data:image/png;base64,"))

    def test_photoimage_arquivo_inexistente_da_erro_claro(self):
        with self.assertRaises(self.tk.TclError):
            self.tk.PhotoImage(file="/nao/existe.png")

    def test_label_e_canvas_aceitam_imagem(self):
        img = self.tk.PhotoImage(data=png_minimo())
        self.tk.Label(self.raiz, image=img)
        self.tk.Button(self.raiz, image=img)
        tela = self.tk.Canvas(self.raiz)
        tela.create_image(10, 10, image=img)

    def test_novos_widgets_existem_no_ttk(self):
        for nome in ("Combobox", "Notebook", "Checkbutton", "Radiobutton", "Scale", "Spinbox"):
            self.assertTrue(hasattr(self.tk.ttk, nome), nome)


if __name__ == "__main__":
    unittest.main()
