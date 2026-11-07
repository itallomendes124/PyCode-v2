"""Executor de código: saída, input, erros, timeout/parada, limpeza, isolamento.

Usa o executor real (android/app/src/main/python) falando por socket com o
ProcessoRemoto, que é o mesmo caminho do APK. O lançador é substituído por um
subprocess local para rodar fora do Android.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ANDROID_PY = RAIZ / "android" / "app" / "src" / "main" / "python"
for p in (str(RAIZ), str(ANDROID_PY)):
    if p not in sys.path:
        sys.path.insert(0, p)

PROC_VIVOS = []


def _lancador(porta, token, pasta, arquivo, erro):
    codigo = (f"import sys; sys.path[:0] = {[str(ANDROID_PY), str(RAIZ)]!r}; "
              f"import pycode_runner; pycode_runner.executar({porta}, {token!r}, {pasta!r}, {arquivo!r}, {erro!r})")
    # A saída do executor é descartada de propósito: ele reporta tudo pelo socket, e um
    # executor que sobra depois do teste não deve sujar a saída dos testes seguintes.
    p = subprocess.Popen([sys.executable, "-c", codigo], cwd=str(pasta),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env={**os.environ, "PYTHONPATH": os.pathsep.join([str(ANDROID_PY), str(RAIZ)])})
    PROC_VIVOS.append(p)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pycode_remoto
        import pycode_servidor as S
        cls.S = S
        pycode_remoto.instalar(_lancador)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.projeto = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def rodar(self, fonte, nome="main.py", entradas=(), parar_apos=None, limite=10):
        (self.projeto / nome).write_text(fonte, encoding="utf-8")
        proc = self.S.Processo(nome, self.projeto)
        saida, codigo, env = "", None, 0
        t0 = time.time()
        while time.time() - t0 < limite:
            time.sleep(0.15)
            if env < len(entradas) and saida.rstrip().endswith((":", "?", ">")):
                proc.escrever(entradas[env] + "\n")
                env += 1
            if parar_apos is not None and time.time() - t0 > parar_apos:
                proc.parar()
                parar_apos = None
            with proc.trava:
                novos = proc.pedacos[:]
            saida = "".join(t for _, t in novos)
            if proc.proc.poll() is not None:
                codigo = proc.proc.returncode
                time.sleep(0.2)
                with proc.trava:
                    saida = "".join(t for _, t in proc.pedacos)
                break
        else:
            proc.parar()
        return saida, codigo


class TestExecucaoBasica(Base):
    def test_print_e_soma(self):
        s, c = self.rodar("print('ola'); print(sum(range(11)))")
        self.assertIn("ola", s)
        self.assertIn("55", s)
        self.assertEqual(c, 0)

    def test_funcoes_e_classes(self):
        s, c = self.rodar("class A:\n def m(self): return 7\nprint(A().m())")
        self.assertIn("7", s)
        self.assertEqual(c, 0)

    def test_import_entre_arquivos(self):
        (self.projeto / "util.py").write_text("def d(x): return x*2\n", encoding="utf-8")
        s, c = self.rodar("from util import d\nprint(d(21))")
        self.assertIn("42", s)

    def test_input(self):
        s, c = self.rodar("n = input('Nome: ')\nprint('oi', n)", entradas=["Ana"])
        self.assertIn("oi Ana", s)

    def test_stderr_separado(self):
        s, c = self.rodar("import sys; sys.stderr.write('falha\\n')")
        self.assertIn("falha", s)

    def test_sys_exit_codigo(self):
        s, c = self.rodar("import sys; print('indo'); sys.exit(3)")
        self.assertEqual(c, 3)


class TestErros(Base):
    def test_excecao_mostra_linha(self):
        s, c = self.rodar("print('a')\n1/0\n")
        self.assertIn("ZeroDivisionError", s)
        self.assertIn("line 2", s)
        self.assertNotEqual(c, 0)

    def test_syntaxerror(self):
        s, c = self.rodar("print('a'\n")
        self.assertIn("SyntaxError", s)


class TestParadaERecursos(Base):
    def test_laco_infinito_parado_de_verdade(self):
        s, c = self.rodar("while True:\n    pass\n", parar_apos=1.2, limite=8)
        self.assertEqual(c, -9)

    def test_nenhum_processo_orfao_apos_parar(self):
        self.rodar("while True:\n    pass\n", parar_apos=1.0, limite=8)
        time.sleep(1.5)
        vivos = [p for p in PROC_VIVOS if p.poll() is None]
        for p in vivos:
            p.kill()
        self.assertEqual(vivos, [])

    def test_saida_excessiva_e_cortada(self):
        s, c = self.rodar("while True:\n    print('x' * 1000)\n", limite=12)
        self.assertLessEqual(len(s), self.S.LIMITE_SAIDA + 100000)


class TestSeguranca(Base):
    def test_token_do_executor_recusa_conexao_sem_token(self):
        # um "programa" que tenta se conectar ao canal do executor sem token não recebe nada
        import socket
        (self.projeto / "main.py").write_text("import time; time.sleep(2)\n", encoding="utf-8")
        proc = self.S.Processo("main.py", self.projeto)
        try:
            s = socket.create_connection(("127.0.0.1", proc.porta), timeout=2)
            s.sendall(b'{"canal":"main","token":"errado","pid":1}\n')
            s.settimeout(1.0)
            try:
                resp = s.recv(100)
            except socket.timeout:
                resp = b""
            self.assertEqual(resp, b"")
            s.close()
        finally:
            proc.parar()


if __name__ == "__main__":
    unittest.main()
