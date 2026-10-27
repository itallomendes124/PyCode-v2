import os
import threading
from pathlib import Path

_estado = {}


def pasta_atual():
    import pycode_servidor as servidor

    return str(servidor.Config.base)


def trocar_pasta(nova, copiar):
    import shutil

    import pycode_servidor as servidor

    nova = Path(nova)
    destino = nova / "projetos"
    destino.mkdir(parents=True, exist_ok=True)
    origem = servidor.Config.projetos()
    copiados = 0
    if copiar and origem.is_dir() and origem.resolve() != destino.resolve():
        for pasta in sorted(origem.iterdir()):
            if not pasta.is_dir() or pasta.name.startswith("."):
                continue
            if (destino / pasta.name).exists():
                continue
            if destino.resolve().is_relative_to(pasta.resolve()):
                continue
            shutil.copytree(pasta, destino / pasta.name)
            copiados += 1
    servidor.Config.base = nova
    if not any(p.is_dir() and not p.name.startswith(".") for p in destino.iterdir()):
        (destino / "treino").mkdir()
        (destino / "treino" / "main.py").write_text("", encoding="utf-8")
    servidor.registrar(f"Pasta dos projetos trocada para {destino} ({copiados} copiados)")
    return copiados


def iniciar(pasta):
    if "porta" in _estado:
        return _estado["porta"]
    app = Path(__file__).resolve().parent
    os.environ["PYCODE_ANDROID"] = "1"
    os.environ["PYCODE_LIBS"] = str(app / "libs" / "ace")
    import pycode_servidor as servidor

    servidor.Config.base = Path(pasta)
    projetos = servidor.Config.projetos()
    projetos.mkdir(parents=True, exist_ok=True)
    if not any(p.is_dir() for p in projetos.iterdir()):
        (projetos / "treino").mkdir()
        (projetos / "treino" / "main.py").write_text("", encoding="utf-8")
    http = servidor.ThreadingHTTPServer(("127.0.0.1", 0), servidor.Manipulador)
    http.daemon_threads = True
    threading.Thread(target=http.serve_forever, daemon=True).start()
    _estado["porta"] = http.server_address[1]
    servidor.registrar(f"PyCode (Android) em http://127.0.0.1:{_estado['porta']}/  (projetos em {projetos})")
    return _estado["porta"]
