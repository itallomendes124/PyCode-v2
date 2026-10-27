import os
import threading
from pathlib import Path

_estado = {}


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
