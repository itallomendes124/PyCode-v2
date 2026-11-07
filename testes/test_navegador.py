"""Interface web e tkinter no navegador real (Playwright).

PULA automaticamente se o Playwright/Chromium não estiver disponível.
"""
import json
import socket
import os
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); from base import subir

try:
    from playwright.sync_api import sync_playwright
    _TEM_PW = True
except Exception:
    _TEM_PW = False


@unittest.skipUnless(_TEM_PW, "Playwright/Chromium não disponível")
class TestInterface(unittest.TestCase):
    def setUp(self):
        # usa o index real do projeto, não o stub
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.S, self.srv, self.porta = subir(tmp)
        # troca o index stub pelo real
        real = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")
        (self.S.WEB / "index.html").write_text(real, encoding="utf-8")
        for nome in ("manifest.webmanifest", "sw.js", "icone-192.png", "icone-512.png", "icone.ico"):
            orig = Path(__file__).resolve().parent.parent / "web" / nome
            if orig.exists():
                (self.S.WEB / nome).write_bytes(orig.read_bytes())

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self._tmp.cleanup()

    def test_pagina_carrega_e_opera_com_token(self):
        B = f"http://127.0.0.1:{self.porta}/"
        erros, falhas = [], []
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pg = nav.new_page()
            pg.on("pageerror", lambda e: erros.append(str(e)))
            pg.on("response", lambda r: falhas.append((r.url, r.status))
                  if "/api/" in r.url and r.status >= 400 else None)
            pg.goto(B)
            pg.wait_for_timeout(1500)
            tok = pg.evaluate("window.__PYCODE_TOKEN")
            self.assertEqual(tok, self.S.TOKEN)
            # cria e salva via API (com token) sem erro
            pg.evaluate("""async () => {
                await API('/api/projeto/criar', {nome: 'nav_proj'});
                await API('/api/arquivo/salvar', {projeto:'nav_proj', nome:'a.py', conteudo:'x=1'});
            }""")
            pg.wait_for_timeout(500)
            lista = pg.evaluate("API('/api/projetos')")
            pg.wait_for_timeout(300)
            nav.close()
        self.assertEqual(erros, [])
        self.assertEqual(falhas, [])

    def test_manifest_e_sw_servidos(self):
        for caminho, tipo in (("/manifest.webmanifest", b"{"), ("/sw.js", b"")):
            req = urllib.request.Request(f"http://127.0.0.1:{self.porta}{caminho}")
            with urllib.request.urlopen(req, timeout=5) as r:
                self.assertEqual(r.status, 200)


    # ---------- botão de executar ----------
    def _abrir(self, pw):
        os.environ["PYCODE_PONTE"] = "1"
        nav = pw.chromium.launch()
        pg = nav.new_page(viewport={"width": 1000, "height": 800})
        pg.goto(f"http://127.0.0.1:{self.porta}/")
        pg.wait_for_timeout(1500)
        return nav, pg

    def _salvar(self, pg, nome, conteudo):
        pg.evaluate(
            "async ([n, c]) => { await API('/api/arquivo/salvar', {projeto: 'meu', nome: n, conteudo: c}); }",
            [nome, conteudo])
        pg.reload()
        pg.wait_for_timeout(1500)
        pg.locator("#arquivos .arquivo", has_text=nome).first.click()
        pg.wait_for_timeout(400)

    def _botao(self, pg):
        return pg.get_attribute("#btn-rodar", "aria-label")

    def test_botao_volta_a_executar_quando_o_programa_termina(self):
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._salvar(pg, "fim.py", "print('acabou')\n")
            pg.click("#btn-rodar")
            pg.wait_for_function("document.getElementById('terminal').innerText.includes('Finalizado')", timeout=12000)
            self.assertEqual(self._botao(pg), "Executar")
            self.assertIn("acabou", pg.inner_text("#terminal"))
            nav.close()

    def test_botao_volta_na_hora_ao_tocar_em_parar(self):
        # O pedido /api/parar é bloqueado de propósito: o servidor nunca fica sabendo.
        # Só a própria página consegue devolver o botão, sem esperar resposta de ninguém.
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._salvar(pg, "laco.py", "import time\nt = time.time()\nwhile time.time() - t < 6:\n    pass\n")
            pg.route("**/api/parar", lambda rota: rota.abort())
            pg.click("#btn-rodar")
            pg.wait_for_timeout(900)
            self.assertEqual(self._botao(pg), "Parar")
            pg.click("#btn-rodar")
            pg.wait_for_timeout(150)
            self.assertEqual(self._botao(pg), "Executar")
            nav.close()

    def test_fechar_janela_tkinter_devolve_o_botao(self):
        programa = ("import tkinter as tk\nj = tk.Tk()\nj.title('t')\n"
                    "tk.Button(j, text='Sair', command=j.destroy).pack()\nj.mainloop()\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._salvar(pg, "janela.py", programa)
            pg.click("#btn-rodar")
            pg.wait_for_selector(".tk-janela", timeout=12000)
            self.assertEqual(self._botao(pg), "Parar")
            pg.click(".tk-fechar")
            pg.wait_for_function("document.querySelectorAll('.tk-janela').length === 0", timeout=8000)
            pg.wait_for_timeout(1200)
            self.assertEqual(self._botao(pg), "Executar")
            nav.close()

    def test_exportar_pelo_botao_da_pagina_funciona_com_token(self):
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            with pg.expect_download() as baixando:
                pg.evaluate("exportarProjeto('meu')")
            self.assertEqual(baixando.value.suggested_filename, "meu.zip")
            nav.close()

    def test_widgets_novos_aparecem_e_respondem(self):
        programa = (
            "import tkinter as tk\nfrom tkinter import ttk\n"
            "j = tk.Tk()\nv = tk.IntVar()\nc = tk.StringVar(value='a')\n"
            "tk.Checkbutton(j, text='ck', variable=v).pack()\n"
            "tk.Radiobutton(j, text='A', variable=c, value='a').pack()\n"
            "tk.Radiobutton(j, text='B', variable=c, value='b').pack()\n"
            "tk.Scale(j, from_=0, to=10, orient='horizontal').pack()\n"
            "tk.Spinbox(j, from_=0, to=5).pack()\n"
            "ttk.Combobox(j, values=['x', 'y']).pack()\n"
            "nb = ttk.Notebook(j); nb.pack()\n"
            "f = tk.Frame(nb); nb.add(f, text='Aba'); tk.Label(f, text='dentro').pack()\n"
            "m = tk.Menu(j); s = tk.Menu(m); s.add_command(label='Oi', command=lambda: print('menu-oi'))\n"
            "m.add_cascade(label='Menu', menu=s); j.config(menu=m)\n"
            "tk.Button(j, text='Ver', command=lambda: print('estado', v.get(), c.get())).pack()\n"
            "j.mainloop()\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._salvar(pg, "widgets.py", programa)
            pg.click("#btn-rodar")
            pg.wait_for_selector(".tk-janela", timeout=12000)
            pg.wait_for_timeout(700)
            j = ".tk-janela "
            self.assertEqual(pg.locator(j + ".tk-checkbutton").count(), 1)
            self.assertEqual(pg.locator(j + ".tk-radiobutton").count(), 2)
            self.assertEqual(pg.locator(j + ".tk-scale").count(), 1)
            self.assertEqual(pg.locator(j + ".tk-spinbox").count(), 1)
            self.assertEqual(pg.locator(j + "select.tk-combobox option").all_inner_texts(), ["x", "y"])
            self.assertEqual(pg.locator(j + ".tk-nb-aba").all_inner_texts(), ["Aba"])
            pg.locator(j + ".tk-checkbutton input").click()
            pg.locator(j + ".tk-radiobutton input").nth(1).click()
            pg.locator(".tk-menu-topo", has_text="Menu").click()
            pg.locator(".tk-menu-popup .tk-menu-item", has_text="Oi").click()
            pg.locator(j + "button.tk-button", has_text="Ver").click()
            pg.wait_for_timeout(500)
            terminal = pg.inner_text("#terminal")
            self.assertIn("menu-oi", terminal)
            self.assertIn("estado 1 b", terminal)
            nav.close()


if __name__ == "__main__":
    unittest.main()
