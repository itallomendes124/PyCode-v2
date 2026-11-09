"""tkinter.font e tkinter.filedialog do tkinter do PyCode.

Usa um TK de mentira que registra o que a página receberia e devolve respostas combinadas.
O que acontece na tela (o seletor aberto, a fonte desenhada) é coberto por test_navegador.py.
"""
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PONTE = RAIZ / "ponte" / "tkinter" / "__init__.py"


class TKFalso:
    def __init__(self, respostas=None):
        self.chamadas = []
        self.respostas = respostas or {}

    def __getattr__(self, nome):
        def chamar(*args):
            self.chamadas.append((nome, args))
            resposta = self.respostas.get(nome)
            return resposta(*args) if callable(resposta) else resposta
        return chamar

    def ultima(self, nome):
        return [a for n, a in self.chamadas if n == nome][-1]


def carregar(respostas=None):
    falso = TKFalso({"abertas": 1, **(respostas or {})})
    navegador = types.ModuleType("browser")
    navegador.window = types.SimpleNamespace(TK=falso)
    sys.modules["browser"] = navegador
    spec = importlib.util.spec_from_file_location("tk_ponte_fontes", PONTE)
    tk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tk)
    return tk, falso


class TestFont(unittest.TestCase):
    def setUp(self):
        self.tk, self.TK = carregar()
        self.Font = self.tk.font.Font

    def test_o_modulo_existe_nos_dois_jeitos_de_importar(self):
        self.assertIs(sys.modules["tkinter.font"], self.tk.font)
        self.assertTrue(callable(self.tk.font.Font))
        for nome in ("NORMAL", "ROMAN", "BOLD", "ITALIC", "families", "names", "nametofont"):
            self.assertTrue(hasattr(self.tk.font, nome), nome)

    def test_padrao(self):
        self.assertEqual(self.Font().actual(),
                         {"family": "Helvetica", "size": 10, "weight": "normal", "slant": "roman",
                          "underline": 0, "overstrike": 0})

    def test_opcoes_viram_o_que_a_pagina_recebe(self):
        f = self.Font(family="Arial", size=14, weight="bold", slant="italic", underline=1)
        self.assertEqual(f._tupla(), ("Arial", 14, "bold italic underline"))
        self.assertEqual(self.Font(family="Arial", size=9)._tupla(), ("Arial", 9, "normal"))

    def test_cget_getitem_setitem_e_configure(self):
        f = self.Font(family="Arial", size=12)
        self.assertEqual(f.cget("size"), 12)
        self.assertEqual(f["family"], "Arial")
        f["size"] = 20
        f.configure(weight="bold")
        self.assertEqual((f.actual("size"), f.actual("weight")), (20, "bold"))
        self.assertEqual(f.configure()["size"], 20)

    def test_opcoes_invalidas_dao_erro_claro(self):
        with self.assertRaises(self.tk.TclError):
            self.Font(cor="vermelho")
        with self.assertRaises(self.tk.TclError):
            self.Font(weight="pesado")
        with self.assertRaises(self.tk.TclError):
            self.Font(size="grande")
        with self.assertRaises(self.tk.TclError):
            self.Font().cget("nada")

    def test_tamanho_negativo_e_em_pixels_e_segue_para_a_pagina(self):
        self.assertEqual(self.Font(family="Arial", size=-20)._tupla(), ("Arial", -20, "normal"))

    def test_descricoes_aceitas(self):
        self.assertEqual(self.Font(font=("Arial", 12, "bold"))._tupla(), ("Arial", 12, "bold"))
        self.assertEqual(self.Font(font="Arial 12 italic")._tupla(), ("Arial", 12, "italic"))
        self.assertEqual(self.Font(font="{Times New Roman} 14 bold underline")._tupla(),
                         ("Times New Roman", 14, "bold underline"))
        base = self.Font(family="Courier", size=11)
        self.assertEqual(self.Font(font=base)._tupla(), ("Courier", 11, "normal"))

    def test_copy_e_independente_e_tem_outro_nome(self):
        a = self.Font(family="Arial", size=12)
        b = a.copy()
        b.configure(size=30)
        self.assertEqual((a["size"], b["size"]), (12, 30))
        self.assertNotEqual(a.name, b.name)
        self.assertNotEqual(a, b)
        self.assertEqual(a, a)

    def test_fontes_nomeadas(self):
        padrao = self.tk.font.nametofont("TkDefaultFont")
        self.assertEqual((padrao["family"], padrao["size"]), ("TkDefaultFont", 10))
        self.assertEqual(self.tk.font.nametofont("TkCaptionFont")["weight"], "bold")
        self.assertIn("TkFixedFont", self.tk.font.names())
        with self.assertRaises(self.tk.TclError):
            self.tk.font.nametofont("NaoExiste")
        mesma = self.Font(name="TkDefaultFont", exists=True)
        self.assertEqual(mesma.name, "TkDefaultFont")

    def test_nome_proprio_e_localizavel(self):
        f = self.Font(name="titulo", family="Arial", size=22)
        self.assertIs(self.tk.font.nametofont("titulo"), f)
        self.assertIn("titulo", self.tk.font.names())

    def test_families_devolve_nomes_ordenados(self):
        familias = self.tk.font.families()
        self.assertIsInstance(familias, tuple)
        self.assertIn("Arial", familias)
        self.assertEqual(list(familias), sorted(familias))

    def test_measure_pergunta_a_pagina(self):
        tk, falso = carregar({"medirTexto": lambda fonte, texto: 7 * len(texto)})
        f = tk.font.Font(family="Arial", size=12, weight="bold")
        self.assertEqual(f.measure("abcd"), 28)
        self.assertEqual(falso.ultima("medirTexto"), (["Arial", 12, "bold"], "abcd"))

    def test_metrics(self):
        tk, falso = carregar({"metricasFonte": {"ascent": 11, "descent": 3, "linespace": 14, "fixed": 0}})
        f = tk.font.Font(size=10)
        self.assertEqual(f.metrics("linespace"), 14)
        self.assertEqual(f.metrics("-ascent"), 11)
        self.assertEqual(f.metrics()["descent"], 3)
        with self.assertRaises(tk.TclError):
            f.metrics("nada")

    def test_widget_recebe_a_fonte_e_acompanha_mudancas(self):
        tk, falso = carregar()
        raiz = tk.Tk()
        f = tk.font.Font(family="Arial", size=12)
        rotulo = tk.Label(raiz, text="oi", font=f)
        enviadas = [json.loads(a[1]) for n, a in falso.chamadas if n == "configurar"]
        self.assertTrue(any(e.get("font") == ["Arial", 12, "normal"] for e in enviadas), enviadas)
        f.configure(size=30, weight="bold")
        ultima = json.loads(falso.ultima("configurar")[1])
        self.assertEqual(ultima["font"], ["Arial", 30, "bold"])
        self.assertEqual(len(f._usos), 1)
        self.assertIs(f._usos[0], rotulo)

    def test_tuplas_antigas_continuam_funcionando(self):
        tk, falso = carregar()
        raiz = tk.Tk()
        tk.Label(raiz, text="x", font=("Arial", 14, "bold"))
        enviadas = [json.loads(a[1]) for n, a in falso.chamadas if n == "configurar"]
        self.assertTrue(any(e.get("font") == ["Arial", 14, "bold"] for e in enviadas), enviadas)


class TestFileDialog(unittest.TestCase):
    def novo(self, resposta):
        return carregar({"escolherArquivo": resposta})

    def test_o_modulo_existe(self):
        tk, _ = carregar()
        self.assertIs(sys.modules["tkinter.filedialog"], tk.filedialog)
        for nome in ("askopenfilename", "askopenfilenames", "asksaveasfilename", "askdirectory",
                     "askopenfile", "askopenfiles", "asksaveasfile"):
            self.assertTrue(callable(getattr(tk.filedialog, nome)), nome)

    def test_abrir_devolve_o_caminho_ou_vazio(self):
        tk, falso = self.novo({"caminhos": ["/a/b.txt"]})
        self.assertEqual(tk.filedialog.askopenfilename(), "/a/b.txt")
        tk, _ = self.novo(None)
        self.assertEqual(tk.filedialog.askopenfilename(), "")

    def test_abrir_varios_devolve_tupla(self):
        tk, _ = self.novo({"caminhos": ["/a/1.txt", "/a/2.txt"]})
        self.assertEqual(tk.filedialog.askopenfilenames(), ("/a/1.txt", "/a/2.txt"))
        tk, _ = self.novo(None)
        self.assertEqual(tk.filedialog.askopenfilenames(), ())

    def test_salvar_acrescenta_a_extensao_padrao_so_quando_falta(self):
        tk, _ = self.novo({"caminhos": ["/a/relatorio"]})
        self.assertEqual(tk.filedialog.asksaveasfilename(defaultextension=".txt"), "/a/relatorio.txt")
        tk, _ = self.novo({"caminhos": ["/a/relatorio.csv"]})
        self.assertEqual(tk.filedialog.asksaveasfilename(defaultextension=".txt"), "/a/relatorio.csv")
        tk, _ = self.novo(None)
        self.assertEqual(tk.filedialog.asksaveasfilename(), "")

    def test_escolher_pasta(self):
        tk, falso = self.novo({"caminhos": ["/a/dados"]})
        self.assertEqual(tk.filedialog.askdirectory(title="Escolha"), "/a/dados")
        self.assertEqual(falso.ultima("escolherArquivo")[0]["modo"], "pasta")

    def test_o_pedido_enviado_a_pagina(self):
        tk, falso = self.novo({"caminhos": ["/x"]})
        tk.filedialog.askopenfilename(
            title="Abrir dados", initialdir="/storage/emulated/0/Download",
            filetypes=[("Texto", "*.txt"), ("Imagens", ("*.png", "*.jpg")), ("Várias", "*.a *.b")])
        pedido = falso.ultima("escolherArquivo")[0]
        self.assertEqual(pedido["modo"], "abrir")
        self.assertEqual(pedido["titulo"], "Abrir dados")
        self.assertEqual(pedido["pasta"], "/storage/emulated/0/Download")
        self.assertEqual(pedido["tipos"], [["Texto", ["*.txt"]], ["Imagens", ["*.png", "*.jpg"]],
                                           ["Várias", ["*.a", "*.b"]]])

    def test_pasta_inicial_padrao_e_a_pasta_do_programa(self):
        tk, falso = self.novo(None)
        tk.filedialog.askopenfilename()
        self.assertEqual(falso.ultima("escolherArquivo")[0]["pasta"], os.getcwd())

    def test_modos_e_opcoes_de_salvar(self):
        tk, falso = self.novo(None)
        tk.filedialog.asksaveasfilename(initialfile="x.txt", defaultextension=".txt", confirmoverwrite=False)
        pedido = falso.ultima("escolherArquivo")[0]
        self.assertEqual((pedido["modo"], pedido["nome"], pedido["extensao"], pedido["sobrescrever"]),
                         ("salvar", "x.txt", ".txt", False))
        tk.filedialog.askopenfilenames()
        self.assertEqual(falso.ultima("escolherArquivo")[0]["modo"], "abrir_varios")

    def test_askopenfile_e_asksaveasfile_devolvem_arquivos_de_verdade(self):
        with tempfile.TemporaryDirectory() as pasta:
            origem = os.path.join(pasta, "a.txt")
            Path(origem).write_text("conteúdo", encoding="utf-8")
            tk, _ = self.novo({"caminhos": [origem]})
            with tk.filedialog.askopenfile() as arq:
                self.assertEqual(arq.read(), "conteúdo")
            destino = os.path.join(pasta, "b.txt")
            tk, _ = self.novo({"caminhos": [destino]})
            with tk.filedialog.asksaveasfile() as arq:
                arq.write("novo")
            self.assertEqual(Path(destino).read_text(), "novo")
            tk, _ = self.novo(None)
            self.assertIsNone(tk.filedialog.askopenfile())
            self.assertIsNone(tk.filedialog.asksaveasfile())

    def test_falha_na_ponte_nao_derruba_o_programa(self):
        def quebra(pedido):
            raise RuntimeError("página indisponível")
        tk, _ = self.novo(quebra)
        self.assertEqual(tk.filedialog.askopenfilename(), "")

    def test_resposta_estranha_vira_cancelamento(self):
        for resposta in ("texto", 42, {"outra": 1}, {"caminhos": None}):
            tk, _ = self.novo(resposta)
            self.assertEqual(tk.filedialog.askopenfilename(), "", resposta)


class TestPonteDeVerdade(unittest.TestCase):
    """Usa a ponte real do executor (tubos), como no Android: o Python pergunta e espera a resposta."""

    def _com_ponte(self, responder):
        import json as _json
        import threading
        saida_r, saida_w = os.pipe()      # Python -> página
        entrada_r, entrada_w = os.pipe()  # página -> Python
        os.environ["PYCODE_TK_OUT"] = str(saida_w)
        os.environ["PYCODE_TK_IN"] = str(entrada_r)
        sys.modules.pop("browser", None)
        recebidos = []

        def pagina():
            buffer = b""
            while True:
                bloco = os.read(saida_r, 65536)
                if not bloco:
                    return
                buffer += bloco
                while b"\n" in buffer:
                    linha, buffer = buffer.split(b"\n", 1)
                    comando = _json.loads(linha)
                    recebidos.append(comando)
                    if "pedido" in comando:
                        valor = responder(comando)
                        os.write(entrada_w, (_json.dumps({"resposta": comando["pedido"], "valor": valor}) + "\n").encode())

        threading.Thread(target=pagina, daemon=True).start()
        spec = importlib.util.spec_from_file_location("tk_ponte_real", PONTE)
        tk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tk)
        return tk, recebidos

    def tearDown(self):
        os.environ.pop("PYCODE_TK_OUT", None)
        os.environ.pop("PYCODE_TK_IN", None)

    def test_o_seletor_espera_a_resposta_da_pagina(self):
        tk, recebidos = self._com_ponte(lambda c: {"caminhos": ["/a/escolhido.txt"]} if c["m"] == "escolherArquivo" else None)
        self.assertEqual(tk.filedialog.askopenfilename(title="Abrir"), "/a/escolhido.txt")
        pedido = [c for c in recebidos if c["m"] == "escolherArquivo"][0]
        self.assertEqual(pedido["a"][0]["titulo"], "Abrir")

    def test_medir_texto_e_metricas_esperam_a_resposta(self):
        def responder(c):
            if c["m"] == "medirTexto":
                return 123
            if c["m"] == "metricasFonte":
                return {"ascent": 9, "descent": 2, "linespace": 11, "fixed": 0}
        tk, _ = self._com_ponte(responder)
        f = tk.font.Font(family="Arial", size=12)
        self.assertEqual(f.measure("texto"), 123)
        self.assertEqual(f.metrics("linespace"), 11)


if __name__ == "__main__":
    unittest.main()
