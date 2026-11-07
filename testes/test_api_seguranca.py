"""API, autenticação por token e segurança HTTP."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import sys as _s; _s.path.insert(0, __import__("os").path.dirname(__file__)); from base import Cliente, subir


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.S, self.srv, porta = subir(Path(self._tmp.name))
        self.c = Cliente(porta, self.S.TOKEN)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self._tmp.cleanup()


class TestAutenticacao(Base):
    def test_token_tem_tamanho_imprevisivel(self):
        self.assertGreaterEqual(len(self.S.TOKEN), 20)

    def test_pagina_injeta_o_token(self):
        st, corpo, _ = self.c.pedir("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn(f'content="{self.S.TOKEN}"'.encode(), corpo)

    def test_rota_sem_token_bloqueada(self):
        st, _ = self.c.jget("/api/projetos", token=None)
        self.assertEqual(st, 403)

    def test_rota_com_token_errado_bloqueada(self):
        st, _ = self.c.jget("/api/projetos", token="token-invalido")
        self.assertEqual(st, 403)

    def test_cabecalho_fixo_1_nao_vale_mais(self):
        st, _, _ = self.c.pedir("GET", "/api/projetos", token=None, host="127.0.0.1")
        self.assertEqual(st, 403)
        # o "1" legado explicitamente recusado
        st2, _ = self.c.jget("/api/projetos", token="1")
        self.assertEqual(st2, 403)

    def test_rota_com_token_certo_ok(self):
        st, dados = self.c.jget("/api/projetos")
        self.assertEqual(st, 200)
        self.assertTrue(any(p["nome"] == "meu" for p in dados["projetos"]))

    def test_vivo_e_publico(self):
        st, dados = self.c.jget("/api/vivo", token=None)
        self.assertEqual(st, 200)
        self.assertEqual(dados["app"], "pycode")


class TestExportacao(Base):
    def test_exportar_sem_token_bloqueado(self):
        st, _, _ = self.c.pedir("GET", "/api/exportar?nome=meu", token=None)
        self.assertEqual(st, 403)

    def test_exportar_com_tk_errado_bloqueado(self):
        st, _, _ = self.c.pedir("GET", "/api/exportar?nome=meu&tk=errado", token=None)
        self.assertEqual(st, 403)

    def test_exportar_com_tk_certo_entrega_zip(self):
        st, corpo, _ = self.c.pedir("GET", f"/api/exportar?nome=meu&tk={self.S.TOKEN}", token=None)
        self.assertEqual(st, 200)
        self.assertEqual(corpo[:2], b"PK")

    def test_exportar_com_cabecalho_tambem_funciona(self):
        st, corpo, _ = self.c.pedir("GET", "/api/exportar?nome=meu")
        self.assertEqual(st, 200)
        self.assertEqual(corpo[:2], b"PK")


class TestHost(Base):
    def test_host_falso_bloqueado(self):
        st, _ = self.c.jget("/api/projetos", host="evil.example.com")
        self.assertEqual(st, 403)

    def test_localhost_aceito(self):
        st, _ = self.c.jget("/api/projetos", host="localhost")
        self.assertEqual(st, 200)


class TestMetodosEErros(Base):
    def test_rota_desconhecida_404(self):
        st, _ = self.c.jget("/api/naoexiste")
        self.assertEqual(st, 404)

    def test_erro_nao_vaza_caminho_interno(self):
        st, corpo, _ = self.c.pedir("GET", "/api/projeto?nome=inexistente")
        self.assertEqual(st, 404)
        self.assertNotIn(b"/", corpo.split(b'"erro"')[1] if b'"erro"' in corpo else b"")
        self.assertNotIn(b"Traceback", corpo)

    def test_json_malformado_400(self):
        st, _, _ = self.c.pedir("POST", "/api/projeto/criar", bruto=b"{quebrado")
        self.assertEqual(st, 400)

    def test_nenhuma_resposta_libera_outros_sites_via_cors(self):
        # sem CORS, o navegador não deixa um site ler as respostas deste servidor
        for caminho, token in (("/", None), ("/api/vivo", None), ("/api/projetos", "padrao"),
                               ("/api/naoexiste", "padrao"), ("/api/projetos", None)):
            _, _, cab = self.c.pedir("GET", caminho, token=token)
            minusculas = {k.lower() for k in cab}
            self.assertNotIn("access-control-allow-origin", minusculas, caminho)

    def test_cabecalho_nosniff_presente(self):
        _, _, cab = self.c.pedir("GET", "/api/vivo", token=None)
        self.assertEqual(cab.get("X-Content-Type-Options"), "nosniff")


class TestChaveDeAbertura(Base):
    """No APK a página só é entregue a quem traz a chave (?k=), que só o WebView recebe."""

    def setUp(self):
        super().setUp()
        self._antes = os.environ.get("PYCODE_EXIGE_CHAVE")

    def tearDown(self):
        if self._antes is None:
            os.environ.pop("PYCODE_EXIGE_CHAVE", None)
        else:
            os.environ["PYCODE_EXIGE_CHAVE"] = self._antes
        super().tearDown()

    def test_sem_a_opcao_a_pagina_abre_normalmente(self):
        os.environ.pop("PYCODE_EXIGE_CHAVE", None)
        st, _, _ = self.c.pedir("GET", "/", token=None)
        self.assertEqual(st, 200)

    def test_com_a_opcao_a_pagina_sem_chave_e_recusada(self):
        os.environ["PYCODE_EXIGE_CHAVE"] = "1"
        for caminho in ("/", "/index.html", "/?k=", "/?outra=1"):
            st, corpo, _ = self.c.pedir("GET", caminho, token=None)
            self.assertEqual(st, 403, caminho)
            self.assertNotIn(self.S.TOKEN.encode(), corpo, caminho)

    def test_chave_errada_e_recusada(self):
        os.environ["PYCODE_EXIGE_CHAVE"] = "1"
        st, _, _ = self.c.pedir("GET", "/?k=chave-errada", token=None)
        self.assertEqual(st, 403)

    def test_chave_certa_entrega_a_pagina_com_o_token(self):
        os.environ["PYCODE_EXIGE_CHAVE"] = "1"
        st, corpo, _ = self.c.pedir("GET", f"/?k={self.S.TOKEN}", token=None)
        self.assertEqual(st, 200)
        self.assertIn(f'content="{self.S.TOKEN}"'.encode(), corpo)

    def test_app_que_so_pede_a_pagina_nao_consegue_o_token(self):
        # o ataque que o token sozinho não impedia: qualquer cliente local pedia "/" e levava o token
        os.environ["PYCODE_EXIGE_CHAVE"] = "1"
        _, corpo, _ = self.c.pedir("GET", "/", token=None)
        self.assertNotIn(b"pycode-token", corpo)
        st, _ = self.c.jget("/api/projetos", token=None)
        self.assertEqual(st, 403)

    def test_rotas_publicas_continuam_abertas(self):
        os.environ["PYCODE_EXIGE_CHAVE"] = "1"
        self.assertEqual(self.c.pedir("GET", "/api/vivo", token=None)[0], 200)
        self.assertEqual(self.c.pedir("GET", "/libs/ace/" + self.S.ARQUIVOS_ACE[0], token=None)[0], 200)

    def test_texto_fora_do_ascii_da_403_e_nao_500(self):
        os.environ["PYCODE_EXIGE_CHAVE"] = "1"
        self.assertEqual(self.c.pedir("GET", "/?k=%C3%A9%C3%A7", token=None)[0], 403)
        self.assertEqual(self.c.pedir("GET", "/api/exportar?nome=meu&tk=%C3%A9", token=None)[0], 403)
        self.assertEqual(self.c.pedir("GET", "/api/projetos", token="\u00e9")[0], 403)


class TestErrosDeConexao(Base):
    """O navegador fechar a conexão não deve poluir o log; erro de verdade deve continuar aparecendo."""

    def _saida_de_handle_error(self, erro):
        captura = io.StringIO()
        with contextlib.redirect_stderr(captura):
            try:
                raise erro
            except Exception:
                self.srv.handle_error(None, ("127.0.0.1", 1))
        return captura.getvalue()

    def test_cliente_que_foi_embora_nao_gera_ruido(self):
        for erro in (ConnectionResetError(), BrokenPipeError(), ConnectionAbortedError()):
            self.assertEqual(self._saida_de_handle_error(erro), "", type(erro).__name__)

    def test_erro_de_verdade_continua_aparecendo(self):
        self.assertIn("ValueError", self._saida_de_handle_error(ValueError("defeito real")))


if __name__ == "__main__":
    unittest.main()
