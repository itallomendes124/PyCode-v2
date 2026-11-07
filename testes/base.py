"""Infraestrutura comum dos testes do PyCode (stdlib: unittest)."""
import importlib
import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def subir(tmp):
    import pycode_servidor as S
    importlib.reload(S)
    web = tmp / "web"
    web.mkdir()
    (web / "index.html").write_text(
        "<html><head><title>t</title></head><body>ok</body></html>", encoding="utf-8")
    libs = tmp / "libs" / "ace"
    libs.mkdir(parents=True)
    for nome in S.ARQUIVOS_ACE:
        alvo = libs / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text("/*x*/", encoding="utf-8")
    S.WEB = web
    S.Config.base = tmp / "dados"
    import os
    os.environ["PYCODE_LIBS"] = str(libs)
    S.Config.projetos().mkdir(parents=True, exist_ok=True)
    (S.Config.projetos() / "meu").mkdir()
    (S.Config.projetos() / "meu" / "main.py").write_text("print('ola')\n", encoding="utf-8")
    srv = S.ThreadingHTTPServer(("127.0.0.1", 0), S.Manipulador)
    porta = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", porta), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    return S, srv, porta


class Cliente:
    def __init__(self, porta, token):
        self.porta = porta
        self.token = token

    def pedir(self, metodo, caminho, corpo=None, token="padrao", host="127.0.0.1", bruto=None):
        cab = {"Host": host}
        tok = self.token if token == "padrao" else token
        if tok is not None:
            cab["X-PyCode-Token"] = tok
        dados = None
        if bruto is not None:
            dados = bruto
        elif corpo is not None:
            dados = json.dumps(corpo).encode("utf-8")
            cab["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.porta}{caminho}", data=dados, headers=cab, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def jget(self, caminho, **kw):
        st, d, _ = self.pedir("GET", caminho, **kw)
        return st, (json.loads(d) if d else None)

    def jpost(self, caminho, corpo=None, **kw):
        st, d, _ = self.pedir("POST", caminho, corpo=corpo, **kw)
        return st, (json.loads(d) if d else None)
