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


    # ---------- tkinter.filedialog e tkinter.font ----------
    def _preparar_arquivos(self):
        projeto = self.S.Config.projetos() / "meu"
        (projeto / "dados.txt").write_text("a,b\n", encoding="utf-8")
        (projeto / "notas.py").write_text("print(1)\n", encoding="utf-8")
        (projeto / "dados").mkdir(exist_ok=True)
        (projeto / "dados" / "x.csv").write_text("1,2\n", encoding="utf-8")
        return projeto

    def _rodar_programa(self, pg, nome, fonte):
        self._salvar(pg, nome, fonte)
        pg.click("#btn-rodar")

    def _linha(self, pg, prefixo):
        pg.wait_for_function("(p) => document.getElementById('terminal').innerText.includes(p)", arg=prefixo, timeout=12000)
        return [l for l in pg.inner_text("#terminal").splitlines() if l.startswith(prefixo)][-1]

    def test_seletor_abrir_devolve_o_caminho_escolhido(self):
        projeto = self._preparar_arquivos()
        programa = ("import tkinter as tk\nfrom tkinter import filedialog\n"
                    "c = filedialog.askopenfilename(filetypes=[('Texto', '*.txt'), ('Python', '*.py')])\n"
                    "print('ESCOLHEU:', c)\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "abrir.py", programa)
            pg.wait_for_selector(".tk-seletor", timeout=12000)
            pg.wait_for_selector(".tk-seletor-item", timeout=12000)
            nomes = pg.locator(".tk-seletor-item .nome").all_inner_texts()
            self.assertIn("dados.txt", nomes)
            self.assertNotIn("notas.py", nomes)  # o filtro inicial é *.txt
            self.assertIn("dados", nomes)        # pastas sempre aparecem
            pg.locator(".tk-seletor-rodape select").select_option(label="Python")
            self.assertIn("notas.py", pg.locator(".tk-seletor-item .nome").all_inner_texts())
            pg.locator(".tk-seletor-rodape select").select_option(label="Texto")
            pg.locator(".tk-seletor-item", has_text="dados.txt").click()
            pg.locator(".tk-seletor-rodape button.principal").click()
            linha = self._linha(pg, "ESCOLHEU:")
            self.assertEqual(Path(linha.split(":", 1)[1].strip()), (projeto / "dados.txt").resolve())
            self.assertEqual(pg.locator(".tk-seletor-fundo").count(), 0)
            nav.close()

    def test_seletor_cancelar_devolve_vazio(self):
        self._preparar_arquivos()
        programa = "import tkinter as tk\nfrom tkinter import filedialog\nprint('ESCOLHEU:', repr(filedialog.askopenfilename()))\n"
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "cancelar.py", programa)
            pg.wait_for_selector(".tk-seletor", timeout=12000)
            pg.wait_for_selector(".tk-seletor-item", timeout=12000)
            self.assertTrue(pg.locator(".tk-seletor-rodape button.principal").is_disabled(), "nada marcado: Abrir deve estar desabilitado")
            pg.locator(".tk-seletor-rodape button", has_text="Cancelar").click()
            self.assertEqual(self._linha(pg, "ESCOLHEU:"), "ESCOLHEU: ''")
            nav.close()

    def test_seletor_salvar_acrescenta_a_extensao_e_recusa_nome_com_barra(self):
        projeto = self._preparar_arquivos()
        programa = ("import tkinter as tk\nfrom tkinter import filedialog\n"
                    "print('SALVOU:', filedialog.asksaveasfilename(defaultextension='.txt'))\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "salvar.py", programa)
            pg.wait_for_selector(".tk-seletor", timeout=12000)
            campo = pg.locator(".tk-seletor-rodape input")
            campo.fill("../fugiu")
            pg.locator(".tk-seletor-rodape button.principal").click()
            self.assertEqual(pg.locator(".tk-seletor").count(), 1, "nome com barra deveria ser recusado")
            campo.fill("relatorio")
            pg.locator(".tk-seletor-rodape button.principal").click()
            linha = self._linha(pg, "SALVOU:")
            self.assertEqual(Path(linha.split(":", 1)[1].strip()), (projeto / "relatorio.txt").resolve())
            nav.close()

    def test_seletor_escolher_pasta(self):
        projeto = self._preparar_arquivos()
        programa = "import tkinter as tk\nfrom tkinter import filedialog\nprint('PASTA:', filedialog.askdirectory())\n"
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "pasta.py", programa)
            pg.wait_for_selector(".tk-seletor", timeout=12000)
            pg.locator(".tk-seletor-item", has_text="dados").first.click()
            pg.wait_for_function("document.querySelector('.tk-seletor-barra .caminho').textContent.endsWith('/dados')")
            self.assertEqual(pg.locator(".tk-seletor-item.apagado").count(), 1)  # x.csv aparece apagado
            pg.locator(".tk-seletor-rodape button.principal").click()
            linha = self._linha(pg, "PASTA:")
            self.assertEqual(Path(linha.split(":", 1)[1].strip()), (projeto / "dados").resolve())
            nav.close()

    def test_seletor_nao_sai_das_pastas_permitidas(self):
        raiz = self.S.Config.projetos().resolve()
        programa = ("import tkinter as tk\nfrom tkinter import filedialog\n"
                    "print('X:', repr(filedialog.askopenfilename(initialdir='/etc')))\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "fora.py", programa)
            pg.wait_for_selector(".tk-seletor", timeout=12000)
            pg.wait_for_function("document.querySelector('.tk-seletor-barra .caminho').textContent.length > 0")
            caminho = pg.locator(".tk-seletor-barra .caminho").inner_text()
            self.assertEqual(Path(caminho), raiz)
            self.assertNotIn("/etc", caminho)
            self.assertTrue(pg.locator(".tk-seletor-barra button", has_text="Subir").is_disabled())
            pg.locator(".tk-seletor-rodape button", has_text="Cancelar").click()
            nav.close()

    def test_parar_o_programa_fecha_o_seletor(self):
        programa = "import tkinter as tk\nfrom tkinter import filedialog\nfiledialog.askopenfilename()\n"
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "preso.py", programa)
            pg.wait_for_selector(".tk-seletor", timeout=12000)
            # o fundo do seletor bloqueia o toque no ■, como numa janela de verdade;
            # aqui o programa é encerrado por dentro, e o seletor não pode ficar pendurado.
            pg.evaluate("parar()")
            pg.wait_for_function("document.querySelectorAll('.tk-seletor-fundo').length === 0", timeout=5000)
            self.assertEqual(self._botao(pg), "Executar")
            nav.close()

    def test_fonte_e_aplicada_medida_e_acompanha_mudancas(self):
        programa = (
            "import tkinter as tk\nfrom tkinter import font\n"
            "j = tk.Tk()\n"
            "f = font.Font(family='Arial', size=24, weight='bold', underline=1)\n"
            "tk.Label(j, text='Titulo', font=f).pack()\n"
            "print('LARGURA:', f.measure('Titulo'))\n"
            "print('LINHA:', f.metrics('linespace'))\n"
            "j.after(900, lambda: f.configure(size=12))\n"
            "tk.Button(j, text='Fechar', command=j.destroy).pack()\n"
            "j.mainloop()\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "fonte.py", programa)
            pg.wait_for_selector(".tk-janela", timeout=12000)
            rotulo = pg.locator(".tk-janela .tk-label").first
            estilo = lambda: rotulo.evaluate("e => { const s = getComputedStyle(e); return [s.fontSize, s.fontWeight, s.textDecorationLine]; }")
            self.assertEqual(estilo()[0], "32px")
            self.assertIn(estilo()[1], ("700", "bold"))
            self.assertIn("underline", estilo()[2])
            largura = int(self._linha(pg, "LARGURA:").split(":")[1])
            linha = int(self._linha(pg, "LINHA:").split(":")[1])
            self.assertGreater(largura, 30)
            self.assertGreater(linha, 20)
            pg.wait_for_function("(e) => getComputedStyle(e).fontSize === '16px'", arg=rotulo.element_handle(), timeout=6000)
            pg.locator(".tk-janela button.tk-button", has_text="Fechar").click()
            nav.close()


    def test_peca_que_expande_cede_espaco_e_o_rodape_continua_visivel(self):
        # No Tk, o rodapé empacotado primeiro mantém o espaço; o Text alto é que encolhe.
        programa = ("import tkinter as tk\nj = tk.Tk()\nj.geometry('300x300')\n"
                    "tk.Label(j, text='RODAPE', relief='sunken').pack(side='bottom', fill='x')\n"
                    "tk.Text(j, height=30, width=20).pack(fill='both', expand=True)\nj.mainloop()\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "rodape.py", programa)
            pg.wait_for_selector(".tk-janela", timeout=12000)
            pg.wait_for_timeout(700)
            medidas = pg.evaluate("""() => {
                const j = document.querySelector('.tk-janela').getBoundingClientRect();
                const r = [...document.querySelectorAll('.tk-janela .tk-label')].find(e => e.textContent === 'RODAPE').getBoundingClientRect();
                const t = document.querySelector('.tk-janela textarea').getBoundingClientRect();
                return {janelaBase: j.bottom, rodapeBase: r.bottom, alturaTexto: t.height};
            }""")
            self.assertLessEqual(medidas["rodapeBase"], medidas["janelaBase"] + 1, medidas)
            self.assertLess(medidas["alturaTexto"], 300, medidas)
            nav.close()

    def test_peca_sem_expand_nao_encolhe(self):
        programa = ("import tkinter as tk\nj = tk.Tk()\nj.geometry('300x120')\n"
                    "tk.Text(j, height=3, width=20).pack()\n"
                    "tk.Button(j, text='Fixo', height=3).pack()\nj.mainloop()\n")
        with sync_playwright() as pw:
            nav, pg = self._abrir(pw)
            self._rodar_programa(pg, "fixo.py", programa)
            pg.wait_for_selector(".tk-janela", timeout=12000)
            pg.wait_for_timeout(500)
            alturas = pg.evaluate("""() => [document.querySelector('.tk-janela textarea').getBoundingClientRect().height,
                                           document.querySelector('.tk-janela button.tk-button').getBoundingClientRect().height]""")
            self.assertGreater(alturas[0], 50, alturas)   # 3 linhas, sem encolher
            self.assertGreater(alturas[1], 40, alturas)
            nav.close()


if __name__ == "__main__":
    unittest.main()
