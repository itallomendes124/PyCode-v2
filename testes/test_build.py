"""Configuração do build: a variante com bibliotecas não pode mudar o APK normal.

Estes testes só leem arquivos (build.gradle.kts, manifest, workflows e o exemplo). Quem compila
de verdade é o GitHub; aqui se garante que a configuração mantém as promessas.
"""
import ast
import importlib.util
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GRADLE = (RAIZ / "android" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
MANIFEST = (RAIZ / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
FLUXO_NORMAL = (RAIZ / ".github" / "workflows" / "apk.yml").read_text(encoding="utf-8")
FLUXO_BIB = (RAIZ / ".github" / "workflows" / "apk-bibliotecas.yml").read_text(encoding="utf-8")
EXEMPLO = (RAIZ / "exemplos" / "teste_bibliotecas.py").read_text(encoding="utf-8")

VERSOES = {"numpy": "numpy==1.26.2", "pandas": "pandas==2.1.3",
           "matplotlib": "matplotlib==3.8.4", "pillow": "pillow==11.0.0",
           "pyparsing": "pyparsing==3.1.4"}


def sem_blocos_condicionais(texto):
    """Remove de `texto` todo bloco `if (comBibliotecas) { ... }`, respeitando as chaves aninhadas."""
    resultado = texto
    while True:
        inicio = resultado.find("if (comBibliotecas) {")
        if inicio < 0:
            return resultado
        abre = resultado.index("{", inicio)
        nivel = 0
        for i in range(abre, len(resultado)):
            if resultado[i] == "{":
                nivel += 1
            elif resultado[i] == "}":
                nivel -= 1
                if nivel == 0:
                    resultado = resultado[:inicio] + resultado[i + 1:]
                    break
        else:
            raise AssertionError("chaves desbalanceadas no build.gradle.kts")


class TestGradle(unittest.TestCase):
    def test_chaves_e_parenteses_balanceados(self):
        self.assertEqual(GRADLE.count("{"), GRADLE.count("}"))
        self.assertEqual(GRADLE.count("("), GRADLE.count(")"))

    def test_a_opcao_so_liga_com_o_parametro(self):
        self.assertIn('val comBibliotecas = project.hasProperty("bibliotecas")', GRADLE)

    def test_pip_e_identificador_so_existem_dentro_da_opcao(self):
        fora = sem_blocos_condicionais(GRADLE)
        for proibido in ("install(", "pip {", "applicationIdSuffix", "versionNameSuffix"):
            self.assertNotIn(proibido, fora, f"{proibido} vazou para o APK normal")

    def test_versoes_fixas_das_bibliotecas(self):
        instaladas = re.findall(r'install\("([^"]+)"\)', GRADLE)
        self.assertEqual(sorted(instaladas), sorted(VERSOES.values()))

    def test_o_nome_do_app_normal_continua_o_mesmo(self):
        fora = sem_blocos_condicionais(GRADLE)
        self.assertIn('manifestPlaceholders["appLabel"] = "PyCode v2"', fora)
        self.assertIn('android:label="${appLabel}"', MANIFEST)

    def test_o_identificador_base_nao_mudou(self):
        self.assertIn('applicationId = "io.github.itallomendes124.pycode"', GRADLE)
        self.assertIn('namespace = "io.github.itallomendes124.pycode"', GRADLE)

    def test_continua_so_arm64_e_python_313(self):
        self.assertIn('abiFilters += listOf("arm64-v8a")', GRADLE)
        self.assertIn('version = "3.13"', GRADLE)
        self.assertIn("minSdk = 24", GRADLE)  # as rodas do Chaquopy são android_24


class TestWorkflows(unittest.TestCase):
    def test_o_fluxo_normal_nao_ganhou_as_bibliotecas(self):
        self.assertIn("branches: [main]", FLUXO_NORMAL)
        self.assertNotIn("-Pbibliotecas", FLUXO_NORMAL)
        self.assertIn("gh release create apk-teste ", FLUXO_NORMAL)

    def test_o_fluxo_das_bibliotecas_so_roda_quando_chamado(self):
        self.assertIn("workflow_dispatch:", FLUXO_BIB)
        self.assertNotIn("push:", FLUXO_BIB)
        self.assertNotIn("pull_request", FLUXO_BIB)

    def test_o_fluxo_das_bibliotecas_compila_com_a_opcao(self):
        self.assertIn("gradle assembleDebug -Pbibliotecas", FLUXO_BIB)

    def test_os_dois_fluxos_nao_mexem_na_release_um_do_outro(self):
        self.assertIn("apk-bibliotecas", FLUXO_BIB)
        self.assertNotIn("apk-teste", FLUXO_BIB)
        self.assertNotIn("apk-bibliotecas", FLUXO_NORMAL)

    def test_grupos_de_concorrencia_diferentes(self):
        grupos = [re.search(r"group: (\S+)", f).group(1) for f in (FLUXO_NORMAL, FLUXO_BIB)]
        self.assertNotEqual(grupos[0], grupos[1])

    def test_nome_do_arquivo_do_apk_das_bibliotecas(self):
        self.assertIn('NOME="PYcodeteste-bibliotecas-${DATA}"', FLUXO_BIB)

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML não instalado")
    def test_yaml_valido(self):
        import yaml
        for texto in (FLUXO_NORMAL, FLUXO_BIB):
            self.assertIn("jobs", yaml.safe_load(texto))


class TestExemplo(unittest.TestCase):
    def test_o_exemplo_compila_e_liga_a_ponte_de_janelas(self):
        ast.parse(EXEMPLO)
        self.assertRegex(EXEMPLO, r"(?m)^import tkinter as tk")

    def test_versoes_esperadas_no_exemplo_batem_com_o_build(self):
        arvore = ast.parse(EXEMPLO)
        esperadas = next(ast.literal_eval(no.value) for no in arvore.body
                         if isinstance(no, ast.Assign) and no.targets[0].id == "ESPERADAS")
        no_build = {"numpy": "1.26.2", "pandas": "2.1.3", "matplotlib": "3.8.4", "PIL": "11.0.0"}
        self.assertEqual(esperadas, no_build)
        for nome, versao in VERSOES.items():
            self.assertIn(versao, GRADLE)

    def test_todos_os_exemplos_compilam(self):
        exemplos = sorted((RAIZ / "exemplos").glob("*.py"))
        self.assertGreaterEqual(len(exemplos), 3)
        for exemplo in exemplos:
            ast.parse(exemplo.read_text(encoding="utf-8"), filename=exemplo.name)

    def test_exemplos_que_abrem_janela_ligam_a_ponte(self):
        # a ponte de janelas só liga com uma linha "import tkinter" escrita no programa
        for nome in ("bloco_de_notas.py", "calculadora.py", "teste_bibliotecas.py"):
            texto = (RAIZ / "exemplos" / nome).read_text(encoding="utf-8")
            self.assertRegex(texto, r"(?m)^(import tkinter|from tkinter import)", nome)

    def test_o_exemplo_usa_matplotlib_sem_janela(self):
        self.assertIn('matplotlib.use("Agg")', EXEMPLO)


if __name__ == "__main__":
    unittest.main()
