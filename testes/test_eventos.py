"""Junção de eventos contínuos no tkinter do PyCode.

Quando o programa demora, os eventos de arrastar um Scale ou de digitar se acumulam. O Tk de verdade
junta os seguidos e entrega só o último. Aqui se garante que isso acontece, e que cliques, teclas e
mudanças de escolha nunca são descartados. Usa a ponte real (tubos), com o dado do evento como texto JSON,
exatamente como a página manda.
"""
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PONTE = RAIZ / "ponte" / "tkinter" / "__init__.py"


class Base(unittest.TestCase):
    def setUp(self):
        self._saida_r, saida_w = os.pipe()      # Python -> página
        entrada_r, self._entrada_w = os.pipe()  # página -> Python
        os.set_blocking(self._saida_r, False)
        os.environ["PYCODE_TK_OUT"] = str(saida_w)
        os.environ["PYCODE_TK_IN"] = str(entrada_r)
        sys.modules.pop("browser", None)
        spec = importlib.util.spec_from_file_location("tk_ponte_eventos", PONTE)
        self.tk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.tk)

    def tearDown(self):
        os.environ.pop("PYCODE_TK_OUT", None)
        os.environ.pop("PYCODE_TK_IN", None)

    def comandos(self):
        try:
            bruto = os.read(self._saida_r, 1 << 20)
        except BlockingIOError:
            return []
        return [json.loads(linha) for linha in bruto.split(b"\n") if linha]

    def cid_de(self, comando, id_widget=None):
        for c in self.comandos():
            if c["m"] == comando and (id_widget is None or c["a"][0] == id_widget):
                return c["a"][1] if comando == "aoMudar" else c["a"][2]
        raise AssertionError(f"comando {comando} não foi enviado")

    def enviar(self, cid, **dados):
        linha = json.dumps({"cid": cid, "dados": json.dumps(dados)}) + "\n"
        os.write(self._entrada_w, linha.encode("utf-8"))

    def processar(self):
        self.tk._processar(False)


class TestJuncao(Base):
    def test_arrastar_o_scale_entrega_so_o_ultimo_valor(self):
        valores = []
        raiz = self.tk.Tk()
        escala = self.tk.Scale(raiz, from_=0, to=100, command=valores.append)
        cid = self.cid_de("aoMudar", escala._id)
        for v in range(30):
            self.enviar(cid, _interno=1, continuo=1, valor=str(v))
        self.processar()
        self.assertEqual(valores, [29])

    def test_digitar_num_campo_entrega_o_texto_completo_uma_vez(self):
        raiz = self.tk.Tk()
        variavel = self.tk.StringVar()
        chamadas = []
        variavel.trace_add("write", lambda *a: chamadas.append(variavel.get()))
        campo = self.tk.Entry(raiz, textvariable=variavel)
        cid = self.cid_de("aoMudar", campo._id)
        for texto in ("a", "ab", "abc"):
            self.enviar(cid, _interno=1, continuo=1, valor=texto)
        self.processar()
        self.assertEqual(variavel.get(), "abc")
        self.assertEqual(chamadas, ["abc"])

    def test_movimento_do_mouse_e_juntado_mas_o_clique_no_meio_nao(self):
        eventos = []
        raiz = self.tk.Tk()
        tela = self.tk.Canvas(raiz)
        tela.bind("<Motion>", lambda e: eventos.append(("move", e.x)))
        tela.bind("<ButtonPress-1>", lambda e: eventos.append(("clique", e.x)))
        cids = {c["a"][1]: c["a"][2] for c in self.comandos() if c["m"] == "bind"}
        cid_move = cids["<Motion>"]
        cid_clique = cids["<ButtonPress-1>"]
        for x in range(5):
            self.enviar(cid_move, type="Motion", x=x, y=0)
        self.enviar(cid_clique, type="ButtonPress", x=99, y=0)
        for x in range(10, 13):
            self.enviar(cid_move, type="Motion", x=x, y=0)
        self.processar()
        self.assertEqual(eventos, [("move", 4), ("clique", 99), ("move", 12)])

    def test_cliques_seguidos_nunca_sao_descartados(self):
        cliques = []
        raiz = self.tk.Tk()
        self.tk.Button(raiz, text="ok", command=lambda: cliques.append(1))
        cid = next(c["a"][1] for c in self.comandos() if c["m"] == "configurar" and "command" in json.loads(c["a"][1]))
        cid = json.loads(cid)["command"]
        for _ in range(10):
            self.enviar(cid, _sem_evento=1)
        self.processar()
        self.assertEqual(len(cliques), 10)

    def test_teclas_seguidas_nunca_sao_descartadas(self):
        teclas = []
        raiz = self.tk.Tk()
        raiz.bind("<Key>", lambda e: teclas.append(e.keysym))
        cid = next(c["a"][2] for c in self.comandos() if c["m"] == "bind")
        for letra in "abcde":
            self.enviar(cid, type="KeyPress", keysym=letra, char=letra)
        self.processar()
        self.assertEqual(teclas, list("abcde"))

    def test_mudancas_de_escolha_seguidas_nao_sao_descartadas(self):
        escolhas = []
        raiz = self.tk.Tk()
        caixa = self.tk.IntVar()
        marca = self.tk.Checkbutton(raiz, variable=caixa, command=lambda: escolhas.append(caixa.get()))
        cid = self.cid_de("aoMudar", marca._id)
        for valor in ("1", "0", "1"):
            self.enviar(cid, _interno=1, valor=valor)
        self.processar()
        self.assertEqual(escolhas, [1, 0, 1])

    def test_widgets_diferentes_alternados_mantem_a_ordem(self):
        vistos = []
        raiz = self.tk.Tk()
        a = self.tk.Scale(raiz, command=lambda v: vistos.append(("a", v)))
        b = self.tk.Scale(raiz, command=lambda v: vistos.append(("b", v)))
        comandos = self.comandos()
        cid_a = next(c["a"][1] for c in comandos if c["m"] == "aoMudar" and c["a"][0] == a._id)
        cid_b = next(c["a"][1] for c in comandos if c["m"] == "aoMudar" and c["a"][0] == b._id)
        self.enviar(cid_a, _interno=1, continuo=1, valor="1")
        self.enviar(cid_b, _interno=1, continuo=1, valor="2")
        self.enviar(cid_a, _interno=1, continuo=1, valor="3")
        self.processar()
        self.assertEqual(vistos, [("a", 1), ("b", 2), ("a", 3)])

    def test_fim_do_programa_ainda_encerra_depois_de_processar_o_que_chegou(self):
        valores = []
        raiz = self.tk.Tk()
        escala = self.tk.Scale(raiz, command=valores.append)
        cid = self.cid_de("aoMudar", escala._id)
        self.enviar(cid, _interno=1, continuo=1, valor="7")
        os.close(self._entrada_w)  # a página fechou: a leitura devolve "fim"
        with self.assertRaises(SystemExit):
            self.processar()
        self.assertEqual(valores, [7])

    def test_dado_estranho_nao_derruba_a_juncao(self):
        raiz = self.tk.Tk()
        os.write(self._entrada_w, b'{"cid": "c1", "dados": "isto nao e json"}\n')
        os.write(self._entrada_w, b'{"cid": "c1", "dados": 42}\n')
        os.write(self._entrada_w, b'{"cid": "c1"}\n')
        self.processar()  # não pode levantar erro


if __name__ == "__main__":
    unittest.main()
