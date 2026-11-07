"""Exemplo exemplos/calculadora.py: lógica pura e segurança do avaliador.

O avaliador usa `ast` em vez de `eval`. Estes testes garantem que ele calcula
certo e recusa qualquer coisa que não seja conta.
"""
import math
import os
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = (RAIZ / "exemplos" / "calculadora.py").read_text(encoding="utf-8")


def carregar():
    # só a parte sem interface: tudo até o ícone (a janela exige tkinter/PyCode)
    cabeca = FONTE[:FONTE.index("def icone_png")]
    cabeca = cabeca.replace("import tkinter as tk\nfrom tkinter import ttk, messagebox\n", "")
    ns = {}
    exec(compile(cabeca, "calculadora.py", "exec"), ns)
    return ns


class TestCalculo(unittest.TestCase):
    def setUp(self):
        self.ns = carregar()
        self.av = self.ns["avaliar"]
        self.ns["CONFIG"]["graus"] = True

    def test_arquivo_compila(self):
        compile(FONTE, "calculadora.py", "exec")

    def test_operacoes_basicas_e_precedencia(self):
        self.assertEqual(self.av("2+3*4"), 14)
        self.assertEqual(self.av("(1+2)*3"), 9)
        self.assertEqual(self.av("-5+2"), -3)
        self.assertEqual(self.av("7×8"), 56)
        self.assertEqual(self.av("10÷4"), 2.5)
        self.assertEqual(self.av("2^10"), 1024)
        self.assertEqual(self.av("1,5+1"), 2.5)

    def test_funcoes_e_constantes(self):
        self.assertEqual(self.av("sqrt(16)"), 4)
        self.assertAlmostEqual(self.av("pi"), math.pi)
        self.assertAlmostEqual(self.av("sqrt(16)+pi"), 4 + math.pi)

    def test_trigonometria_em_graus_e_radianos(self):
        self.assertAlmostEqual(self.av("sin(30)"), 0.5)
        self.ns["CONFIG"]["graus"] = False
        self.assertAlmostEqual(self.av("sin(30)"), math.sin(30))

    def test_variavel_x_so_existe_quando_informada(self):
        self.assertAlmostEqual(self.av("x*2", 4), 8)
        with self.assertRaises(ValueError):
            self.av("x*2")

    def test_erros_comuns(self):
        with self.assertRaises(ZeroDivisionError):
            self.av("1/0")
        for ruim in ("(", "2+", "3 3", ""):
            with self.assertRaises(Exception, msg=ruim):
                self.av(ruim)


class TestSeguranca(unittest.TestCase):
    def setUp(self):
        self.av = carregar()["avaliar"]

    def test_recusa_codigo_que_nao_e_conta(self):
        perigosos = [
            "__import__('os').system('echo oi')",
            "open('/etc/passwd').read()",
            "().__class__.__bases__",
            "(lambda: 1)()",
            "[i for i in range(3)]",
            "'abc'",
            "print(1)",
            "eval('1+1')",
            "sin.__globals__",
            "abs(1, 2)",
            "x",
        ]
        for texto in perigosos:
            with self.assertRaises(Exception, msg=texto):
                self.av(texto)

    def test_expoente_gigante_nao_trava(self):
        for texto in ("2**99999999", "9^9^9", "10^1001"):
            with self.assertRaises(ValueError, msg=texto):
                self.av(texto)

    def test_nao_usa_eval_nem_exec(self):
        sem_comentarios = "\n".join(l for l in FONTE.splitlines() if not l.strip().startswith("#"))
        self.assertNotIn("eval(", sem_comentarios.replace("avaliar(", "").replace("'eval('", ""))
        self.assertNotIn("exec(", sem_comentarios)


class TestConversor(unittest.TestCase):
    def setUp(self):
        self.conv = carregar()["converter"]

    def test_temperatura(self):
        self.assertAlmostEqual(self.conv(100, "Temperatura", "°C", "°F"), 212)
        self.assertAlmostEqual(self.conv(0, "Temperatura", "°C", "K"), 273.15)
        self.assertAlmostEqual(self.conv(32, "Temperatura", "°F", "°C"), 0)

    def test_comprimento_e_massa(self):
        self.assertAlmostEqual(self.conv(1, "Comprimento", "km", "m"), 1000)
        self.assertAlmostEqual(self.conv(1, "Massa", "lb", "kg"), 0.45359237)


if __name__ == "__main__":
    unittest.main()
