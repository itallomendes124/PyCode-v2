"""O README e as notas não podem prometer (nem negar) o que o código não faz."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
README = (RAIZ / "README.md").read_text(encoding="utf-8")
NOTAS = (RAIZ / "android" / "NOTAS.md").read_text(encoding="utf-8")
SHIM = (RAIZ / "ponte" / "tkinter" / "__init__.py").read_text(encoding="utf-8")

CLASSES_QUE_EXISTEM = ("Label", "Button", "Entry", "Text", "Canvas", "Frame", "Listbox", "Checkbutton",
                       "Radiobutton", "Scale", "Spinbox", "Menu", "PhotoImage", "Combobox", "Notebook")
NAO_EXISTEM = ("Treeview", "Progressbar", "PanedWindow", "colorchooser", "scrolledtext")


class TestReadme(unittest.TestCase):
    def test_o_que_o_texto_diz_que_existe_existe(self):
        for nome in CLASSES_QUE_EXISTEM:
            self.assertRegex(SHIM, rf"(?m)^class {nome}\b", nome)
            self.assertRegex(README, rf"`(?:ttk\.)?{nome}\b", f"{nome} deveria constar no README")
        for modulo in ("tkinter.font", "tkinter.filedialog"):
            self.assertIn(f'_Modulo("{modulo}")', SHIM, modulo)
            self.assertIn(f"`{modulo}`", README, modulo)

    def test_o_que_o_texto_diz_que_nao_existe_realmente_nao_existe(self):
        for nome in NAO_EXISTEM:
            self.assertIn(nome, README, f"{nome} deveria constar entre os que faltam")
            self.assertNotRegex(SHIM, rf"(?m)^class {nome}\b", nome)
            self.assertNotIn(f'"tkinter.{nome}"', SHIM, nome)

    def test_nao_ficou_o_texto_antigo_sobre_senha(self):
        self.assertNotIn("não tem senha", README)
        self.assertNotIn("127.0.0.1:8765. Instale", README)

    def test_nenhum_item_de_lista_repetido(self):
        itens = [linha.strip() for linha in README.splitlines() if linha.startswith("- ")]
        repetidos = {i for i in itens if itens.count(i) > 1}
        self.assertEqual(repetidos, set())

    def test_a_secao_limites_fala_do_pip_e_das_bibliotecas_nativas(self):
        limites = README[README.index("## Limites"):README.index("## Segurança")]
        for trecho in ("pip", "NumPy", "SciPy", "VS Code", "seletor próprio"):
            self.assertIn(trecho, limites, trecho)

    def test_o_readme_cita_a_secao_de_seguranca_e_a_de_testes(self):
        self.assertIn("## Segurança", README)
        self.assertIn("## Testes", README)


class TestNotas(unittest.TestCase):
    def test_as_notas_listam_font_e_filedialog(self):
        self.assertIn("tkinter.font", NOTAS)
        self.assertIn("tkinter.filedialog", NOTAS)

    def test_o_nome_do_apk_nas_notas_e_o_novo(self):
        self.assertIn("PYcodeteste-AAAA-MM-DD.apk", NOTAS)
        self.assertNotIn("PyCode-v2.apk", NOTAS)


if __name__ == "__main__":
    unittest.main()
