"""Projetos, arquivos, traversal de caminhos e importação de .zip."""
import io
import tempfile
import unittest
import urllib.parse
import zipfile
from pathlib import Path

import sys as _s; _s.path.insert(0, __import__("os").path.dirname(__file__)); from base import Cliente, subir


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.S, self.srv, porta = subir(Path(self._tmp.name))
        self.c = Cliente(porta, self.S.TOKEN)
        self.raiz = self.S.Config.projetos()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self._tmp.cleanup()


class TestProjetos(Base):
    def test_criar_listar_excluir(self):
        st, _ = self.c.jpost("/api/projeto/criar", {"nome": "projeto_x"})
        self.assertEqual(st, 200)
        self.assertTrue((self.raiz / "projeto_x").is_dir())
        _, lista = self.c.jget("/api/projetos")
        self.assertIn("projeto_x", [p["nome"] for p in lista["projetos"]])
        st, _ = self.c.jpost("/api/projeto/excluir", {"nome": "projeto_x"})
        self.assertEqual(st, 200)

    def test_renomear(self):
        self.c.jpost("/api/projeto/criar", {"nome": "antigo"})
        st, _ = self.c.jpost("/api/projeto/renomear", {"nome": "antigo", "novo": "atual"})
        self.assertEqual(st, 200)
        self.assertTrue((self.raiz / "atual").is_dir())

    def test_projeto_inexistente_404(self):
        st, _ = self.c.jget("/api/projeto?nome=fantasma")
        self.assertEqual(st, 404)


class TestArquivos(Base):
    def test_salvar_e_ler(self):
        st, _ = self.c.jpost("/api/arquivo/salvar",
                             {"projeto": "meu", "nome": "a.py", "conteudo": "x = 1\n"})
        self.assertEqual(st, 200)
        self.assertEqual((self.raiz / "meu" / "a.py").read_text(), "x = 1\n")

    def test_arquivo_grande_rejeitado(self):
        grande = "a" * (self.S.LIMITE_ARQUIVO + 10)
        st, _ = self.c.jpost("/api/arquivo/salvar",
                             {"projeto": "meu", "nome": "g.py", "conteudo": grande})
        self.assertEqual(st, 400)

    def test_extensao_invalida_rejeitada(self):
        st, _ = self.c.jpost("/api/arquivo/salvar",
                             {"projeto": "meu", "nome": "x.exe", "conteudo": "a"})
        self.assertEqual(st, 400)


class TestTraversal(Base):
    def test_traversal_no_nome_do_arquivo(self):
        for nome in ("../fora.py", "..%2ffora.py", "sub/dir.py", "/etc/passwd"):
            st, _ = self.c.jpost("/api/arquivo/salvar",
                                 {"projeto": "meu", "nome": nome, "conteudo": "x"})
            self.assertEqual(st, 400, nome)
        self.assertFalse((Path(self._tmp.name) / "dados" / "fora.py").exists())

    def test_traversal_no_nome_do_projeto(self):
        for nome in ("../../etc", "..%2f..%2fetc", "/etc", "meu/../../x"):
            st, _, _ = self.c.pedir("GET", f"/api/exportar?nome={nome}&tk={self.S.TOKEN}", token=None)
            self.assertIn(st, (400, 404), nome)


class TestZip(Base):
    def _zip(self, arquivos):
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            for nome, dados in arquivos:
                z.writestr(nome, dados)
        return mem.getvalue()

    def test_importar_zip_valido(self):
        pacote = self._zip([("a.py", "print(1)\n"), ("b.py", "print(2)\n")])
        st, dados = self.c.jpost("/api/importar?nome=importado", bruto=pacote)
        self.assertEqual(st, 200)
        self.assertTrue((self.raiz / dados["nome"] / "a.py").exists())

    def test_zip_invalido_rejeitado(self):
        st, _ = self.c.jpost("/api/importar?nome=x", bruto=b"isto nao e um zip")
        self.assertEqual(st, 400)

    def test_zip_com_muitas_entradas_rejeitado(self):
        pacote = self._zip([(f"a{i}.py", "x=1\n") for i in range(self.S.LIMITE_ZIP_ENTRADAS + 50)])
        st, dados = self.c.jpost("/api/importar?nome=muitos", bruto=pacote)
        self.assertEqual(st, 400)
        self.assertIn("entradas", dados["erro"])

    def test_zip_bomb_por_razao_rejeitado(self):
        # ~5 MB de zeros comprimem demais: razão altíssima
        pacote = self._zip([("bomba.py", b"\x00" * 5_000_000)])
        st, dados = self.c.jpost("/api/importar?nome=bomba", bruto=pacote)
        self.assertEqual(st, 400)

    def test_traversal_dentro_do_zip_neutralizado(self):
        pacote = self._zip([("../../fora.py", "print('escapou')\n"), ("ok.py", "print('ok')\n")])
        st, dados = self.c.jpost("/api/importar?nome=trav", bruto=pacote)
        self.assertEqual(st, 200)
        # só o nome-base entra; nada escapa da pasta de projetos
        destino = self.raiz / dados["nome"]
        nomes = [p.name for p in destino.iterdir()]
        self.assertIn("fora.py", nomes)  # achatado para o nome-base
        self.assertFalse((Path(self._tmp.name) / "dados" / "fora.py").exists())


class TestListarPasta(Base):
    """Rota usada pelo seletor de arquivos (tkinter.filedialog). Só lista nomes, só em pastas permitidas."""

    def _listar(self, caminho=None, **kw):
        alvo = "/api/pasta" + ("?caminho=" + urllib.parse.quote(str(caminho)) if caminho is not None else "")
        return self.c.jget(alvo, **kw)

    def setUp(self):
        super().setUp()
        (self.raiz / "meu" / "dados").mkdir()
        (self.raiz / "meu" / "dados" / "x.csv").write_text("a,b\n", encoding="utf-8")
        (self.raiz / "meu" / ".oculto").write_text("segredo", encoding="utf-8")
        (self.raiz / "meu" / "zeta.txt").write_text("z", encoding="utf-8")

    def test_sem_caminho_lista_a_raiz_dos_projetos(self):
        st, d = self._listar()
        self.assertEqual(st, 200)
        self.assertEqual(Path(d["caminho"]), self.raiz.resolve())
        self.assertIsNone(d["pai"])
        self.assertIn("meu", [i["nome"] for i in d["itens"]])

    def test_lista_pastas_primeiro_e_esconde_ocultos(self):
        st, d = self._listar(self.raiz / "meu")
        self.assertEqual(st, 200)
        nomes = [i["nome"] for i in d["itens"]]
        self.assertEqual(nomes, ["dados", "main.py", "zeta.txt"])
        self.assertNotIn(".oculto", nomes)
        self.assertTrue(d["itens"][0]["pasta"])
        self.assertEqual(Path(d["pai"]), self.raiz.resolve())

    def test_exige_o_token(self):
        st, _ = self._listar(self.raiz, token=None)
        self.assertEqual(st, 403)
        st, _ = self._listar(self.raiz, token="errado")
        self.assertEqual(st, 403)

    def test_recusa_pastas_fora_das_permitidas(self):
        for fora in ("/", "/etc", "/tmp", str(self.raiz.parent), str(self.raiz / ".." / "..")):
            st, d = self._listar(fora)
            self.assertEqual(st, 403, fora)

    def test_recusa_subir_com_ponto_ponto(self):
        st, _ = self._listar(str(self.raiz / "meu" / ".." / ".." / ".."))
        self.assertEqual(st, 403)

    def test_recusa_atalho_que_aponta_para_fora(self):
        fora = Path(self._tmp.name) / "fora"
        fora.mkdir()
        (fora / "segredo.txt").write_text("x", encoding="utf-8")
        try:
            (self.raiz / "meu" / "atalho").symlink_to(fora, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("o sistema não permite links simbólicos")
        st, _ = self._listar(self.raiz / "meu" / "atalho")
        self.assertEqual(st, 403)

    def test_pasta_inexistente_ou_arquivo_da_404(self):
        self.assertEqual(self._listar(self.raiz / "nao_existe")[0], 404)
        self.assertEqual(self._listar(self.raiz / "meu" / "zeta.txt")[0], 404)

    def test_limite_de_itens(self):
        self.S.LIMITE_LISTAGEM = 3
        for i in range(10):
            (self.raiz / "meu" / f"a{i}.txt").write_text("x", encoding="utf-8")
        st, d = self._listar(self.raiz / "meu")
        self.assertEqual((st, len(d["itens"])), (200, 3))

    def test_nao_devolve_conteudo_de_arquivo(self):
        st, d = self._listar(self.raiz / "meu")
        self.assertNotIn("segredo", str(d))
        self.assertEqual(set(d["itens"][0]), {"nome", "pasta", "tamanho"})


if __name__ == "__main__":
    unittest.main()
