import argparse
import ast
import builtins
import codecs
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

VERSAO_ACE = "1.32.6"
URL_ACE = f"https://cdnjs.cloudflare.com/ajax/libs/ace/{VERSAO_ACE}/"
ARQUIVOS_ACE = ["ace.js", "ext-language_tools.js", "ext-searchbox.js", "mode-python.js", "keybinding-vscode.js", "snippets/python.js"]
APP = Path(__file__).resolve().parent
WEB = APP / "web"
PONTE = APP / "ponte"
NOME_ARQUIVO = re.compile(r"^[A-Za-z0-9_\-]+\.(py|txt|md|json|csv)$", re.IGNORECASE)
PROIBIDOS_PROJETO = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
RESERVADOS = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)}, *{f"LPT{i}" for i in range(1, 10)}}
LIMITE_ARQUIVO = 1_000_000
LIMITE_SAIDA = 2_000_000
TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json",
         ".webmanifest": "application/manifest+json", ".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml"}


class Config:
    base = Path(os.environ.get("PYCODE_PASTA", Path.home() / "PyCode"))
    janela = False

    @classmethod
    def projetos(cls):
        return cls.base / "projetos"

    @classmethod
    def lixeira(cls):
        return cls.base / ".lixeira"

    @classmethod
    def libs(cls):
        if os.environ.get("PYCODE_LIBS"):
            return Path(os.environ["PYCODE_LIBS"])
        return cls.base / ".libs" / "ace"


def registrar(msg):
    try:
        Config.base.mkdir(parents=True, exist_ok=True)
        with open(Config.base / "pycode.log", "a", encoding="utf-8") as log:
            log.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass
    print(msg)


class ErroUsuario(Exception):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status


def validar_projeto(nome):
    nome = str(nome or "").strip()
    if not nome or len(nome) > 60 or nome.startswith(".") or nome.endswith(".") or PROIBIDOS_PROJETO.search(nome):
        raise ErroUsuario("Nome de projeto inválido. Evite / \\ : * ? \" < > |")
    if nome.split(".")[0].upper() in RESERVADOS:
        raise ErroUsuario("Esse nome é reservado pelo Windows.")
    return nome


def validar_arquivo(nome):
    nome = str(nome or "").strip()
    if not NOME_ARQUIVO.match(nome):
        raise ErroUsuario("Nome de arquivo inválido. Use letras, números, _ ou - e extensão .py, .txt, .md, .json ou .csv.")
    return nome


def pasta_projeto(nome, existir=True):
    raiz = Config.projetos().resolve()
    caminho = (raiz / validar_projeto(nome)).resolve()
    if caminho.parent != raiz:
        raise ErroUsuario("Caminho inválido.")
    if existir and not caminho.is_dir():
        raise ErroUsuario("Projeto não encontrado.", 404)
    return caminho


def caminho_arquivo(projeto, nome):
    pasta = pasta_projeto(projeto)
    caminho = (pasta / validar_arquivo(nome)).resolve()
    if caminho.parent != pasta:
        raise ErroUsuario("Caminho inválido.")
    return caminho


def ler_arquivos(pasta):
    arquivos = {}
    for item in sorted(pasta.iterdir()):
        if item.is_file() and NOME_ARQUIVO.match(item.name) and item.stat().st_size <= LIMITE_ARQUIVO:
            try:
                arquivos[item.name] = item.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                arquivos[item.name] = item.read_text(encoding="latin-1")
    return arquivos


def nome_livre(base):
    base = validar_projeto(base)
    if not (Config.projetos() / base).exists():
        return base
    i = 2
    while (Config.projetos() / f"{base} {i}").exists():
        i += 1
    return f"{base} {i}"


def mandar_lixeira(caminho, rotulo):
    Config.lixeira().mkdir(parents=True, exist_ok=True)
    destino = Config.lixeira() / f"{time.strftime('%Y%m%d-%H%M%S')}-{rotulo}"
    shutil.move(str(caminho), str(destino))


def listar_projetos():
    Config.projetos().mkdir(parents=True, exist_ok=True)
    lista = []
    for pasta in Config.projetos().iterdir():
        if not pasta.is_dir() or pasta.name.startswith("."):
            continue
        arquivos = [p for p in pasta.iterdir() if p.is_file() and NOME_ARQUIVO.match(p.name)]
        datas = [p.stat().st_mtime for p in arquivos] + [pasta.stat().st_mtime]
        lista.append({"nome": pasta.name, "arquivos": len(arquivos), "atualizado": int(max(datas) * 1000)})
    lista.sort(key=lambda p: -p["atualizado"])
    return lista


TRADUCOES = [
    (r"invalid syntax\. Perhaps you forgot a comma\?", "Sintaxe inválida. Esqueceu uma vírgula?"),
    (r"invalid syntax\. Maybe you meant '==' or ':=' instead of '='\?", "Sintaxe inválida. Queria comparar com '==' em vez de '='?"),
    (r"invalid syntax\. Maybe you meant .*", "Sintaxe inválida"),
    (r"invalid syntax", "Sintaxe inválida"),
    (r"expected ':'", "Faltou ':' no fim da linha"),
    (r"expected '\('", "Faltou '('"),
    (r"expected an indented block.*", "Faltou indentar o bloco abaixo desta linha"),
    (r"unexpected indent", "Indentação inesperada"),
    (r"unindent does not match any outer indentation level", "A indentação não bate com nenhum nível anterior"),
    (r"inconsistent use of tabs and spaces.*", "Mistura de Tab e espaços na indentação"),
    (r"unterminated triple-quoted string literal.*", "String com aspas triplas não foi fechada"),
    (r"unterminated string literal.*", "A string não foi fechada"),
    (r"'(.)' was never closed", r"O '\1' foi aberto e nunca fechado"),
    (r"unmatched '(.)'", r"O '\1' foi fechado sem ter sido aberto"),
    (r"closing parenthesis '(.)' does not match opening parenthesis '(.)'.*", r"O '\1' não fecha o '\2' que foi aberto"),
    (r"Missing parentheses in call to 'print'.*", "Faltam parênteses: use print(...)"),
    (r"invalid decimal literal", "Número inválido (letra colada num número?)"),
    (r"cannot assign to function call.*", "Não dá para atribuir valor a uma chamada de função"),
    (r"cannot assign to literal.*", "Não dá para atribuir valor a um literal"),
    (r"cannot assign to (.*?)(?: here)?\..*", r"Não dá para atribuir valor a \1"),
    (r"'return' outside function", "'return' fora de uma função"),
    (r"'break' outside loop", "'break' fora de um laço"),
    (r"'continue' not properly in loop", "'continue' fora de um laço"),
    (r"'await' outside (async )?function", "'await' fora de uma função async"),
    (r"invalid character '(.)'.*", r"Caractere inválido '\1'"),
    (r"invalid non-printable character.*", "Caractere invisível inválido no código"),
]
NOMES_PADRAO = set(dir(builtins)) | {"__name__", "__file__", "__doc__", "__builtins__", "__spec__", "__loader__", "__package__"}
CACHE_MODULOS = {}


def traduzir(msg):
    msg = str(msg or "")
    for padrao, texto in TRADUCOES:
        achado = re.match(padrao, msg)
        if achado:
            return achado.expand(texto)
    return msg


def problema(linha, coluna, fim, msg, tipo):
    return {"linha": linha or 1, "coluna": max(coluna or 0, 0), "fim": fim, "msg": msg, "tipo": tipo}


def erro_sintaxe(erro):
    coluna = (erro.offset or 1) - 1
    fim = getattr(erro, "end_offset", None)
    mesma = getattr(erro, "end_lineno", erro.lineno) == erro.lineno
    fim = fim - 1 if fim and mesma and fim - 1 > coluna else None
    return [problema(erro.lineno, coluna, fim, traduzir(erro.msg), "error")]


def modulo_existe(nome):
    if nome not in CACHE_MODULOS:
        try:
            CACHE_MODULOS[nome] = importlib.util.find_spec(nome) is not None
        except (ImportError, ValueError):
            CACHE_MODULOS[nome] = False
    return CACHE_MODULOS[nome]


def analisar(codigo, nome, modulos_projeto):
    try:
        arvore = ast.parse(codigo, nome)
        compile(codigo, nome, "exec")
    except SyntaxError as erro:
        return erro_sintaxe(erro)
    except ValueError:
        return [problema(1, 0, None, "O arquivo tem caracteres inválidos", "error")]
    definidos = set(NOMES_PADRAO)
    usados = set()
    importados = {}
    estrela = False
    lista = []
    for no in ast.walk(arvore):
        tipo = type(no).__name__
        if isinstance(no, ast.Name):
            (usados if isinstance(no.ctx, ast.Load) else definidos).add(no.id)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definidos.add(no.name)
        elif isinstance(no, ast.arg):
            definidos.add(no.arg)
        elif isinstance(no, (ast.Import, ast.ImportFrom)):
            modulos = [a.name for a in no.names] if isinstance(no, ast.Import) else ([no.module] if no.module and not no.level else [])
            for mod in modulos:
                topo = mod.split(".")[0]
                if topo not in modulos_projeto and not modulo_existe(topo):
                    lista.append(problema(no.lineno, no.col_offset, getattr(no, "end_col_offset", None),
                                          f"Módulo '{topo}' não encontrado. Instale com: pip install {topo}", "warning"))
            for apelido in no.names:
                if apelido.name == "*":
                    estrela = True
                    continue
                local = apelido.asname or apelido.name.split(".")[0]
                definidos.add(local)
                importados.setdefault(local, no)
        elif isinstance(no, ast.ExceptHandler) and no.name:
            definidos.add(no.name)
        elif isinstance(no, (ast.Global, ast.Nonlocal)):
            definidos.update(no.names)
        elif tipo in ("MatchAs", "MatchStar") and getattr(no, "name", None):
            definidos.add(no.name)
        elif tipo == "MatchMapping" and getattr(no, "rest", None):
            definidos.add(no.rest)
    if not estrela:
        for no in ast.walk(arvore):
            if isinstance(no, ast.Name) and isinstance(no.ctx, ast.Load) and no.id not in definidos:
                fim = getattr(no, "end_col_offset", None) or no.col_offset + len(no.id)
                lista.append(problema(no.lineno, no.col_offset, fim, f"'{no.id}' não está definido", "error"))
    for local, no in importados.items():
        if local not in usados:
            fim = getattr(no, "end_col_offset", None) if getattr(no, "end_lineno", no.lineno) == no.lineno else None
            lista.append(problema(no.lineno, no.col_offset, fim, f"'{local}' foi importado, mas nunca é usado", "warning"))
    lista.sort(key=lambda p: (p["linha"], p["coluna"]))
    return lista


def usar_ponte():
    escolha = os.environ.get("PYCODE_PONTE")
    if escolha in ("0", "1"):
        return escolha == "1"
    if os.name == "nt" or sys.platform == "darwin":
        return False
    return not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")


def interpretador():
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and exe.with_name("python.exe").exists():
        return str(exe.with_name("python.exe"))
    return str(exe)


class Processo:
    todos = {}

    def __init__(self, arquivo, pasta):
        self.id = uuid.uuid4().hex[:12]
        self.pedacos = []
        self.tamanho = 0
        self.trava = threading.Lock()
        self.criado = time.time()
        ambiente = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        self.tk = []
        self.tk_base = 0
        self.fd_eventos = None
        extras = {}
        if usar_ponte() and (PONTE / "tkinter" / "__init__.py").exists():
            leitura_cmd, escrita_cmd = os.pipe()
            leitura_evt, escrita_evt = os.pipe()
            ambiente["PYCODE_TK_OUT"] = str(escrita_cmd)
            ambiente["PYCODE_TK_IN"] = str(leitura_evt)
            ambiente["PYTHONPATH"] = str(PONTE) + (os.pathsep + ambiente["PYTHONPATH"] if ambiente.get("PYTHONPATH") else "")
            extras["pass_fds"] = (escrita_cmd, leitura_evt)
        self.proc = subprocess.Popen([interpretador(), "-u", arquivo], cwd=str(pasta), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ambiente, creationflags=flags, **extras)
        self.leitores = [threading.Thread(target=self._ler, args=(self.proc.stdout, "out"), daemon=True),
                         threading.Thread(target=self._ler, args=(self.proc.stderr, "err"), daemon=True)]
        if extras:
            os.close(escrita_cmd)
            os.close(leitura_evt)
            self.fd_eventos = escrita_evt
            self.leitores.append(threading.Thread(target=self._ler_tk, args=(leitura_cmd,), daemon=True))
        for leitor in self.leitores:
            leitor.start()
        Processo.todos[self.id] = self
        Processo.limpar()

    def _anexar(self, tipo, texto):
        with self.trava:
            if self.tamanho > LIMITE_SAIDA:
                return
            self.tamanho += len(texto)
            self.pedacos.append([tipo, texto])
            if self.tamanho > LIMITE_SAIDA:
                self.pedacos.append(["err", "\n[PyCode] Saída grande demais. O programa foi parado.\n"])
                self.parar()

    def _ler(self, fluxo, tipo):
        decodificador = codecs.getincrementaldecoder("utf-8")("replace")
        leitura = getattr(fluxo, "read1", None) or fluxo.read
        while True:
            try:
                bloco = leitura(4096)
            except (OSError, ValueError):
                break
            if not bloco:
                break
            texto = decodificador.decode(bloco)
            if texto:
                self._anexar(tipo, texto)
        resto = decodificador.decode(b"", final=True)
        if resto:
            self._anexar(tipo, resto)

    def _ler_tk(self, fd):
        with os.fdopen(fd, "rb") as fluxo:
            for linha in fluxo:
                try:
                    comando = json.loads(linha.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                with self.trava:
                    self.tk.append(comando)
        self._fechar_eventos()

    def _fechar_eventos(self):
        fd, self.fd_eventos = self.fd_eventos, None
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    def enviar_tk(self, mensagem):
        if self.fd_eventos is None:
            return
        dados = (json.dumps(mensagem) + "\n").encode("utf-8")
        try:
            while dados:
                escrito = os.write(self.fd_eventos, dados)
                dados = dados[escrito:]
        except OSError:
            self._fechar_eventos()

    def ler(self, desde, desde_tk=0):
        terminou = self.proc.poll() is not None and not any(l.is_alive() for l in self.leitores)
        with self.trava:
            novos = self.pedacos[desde:]
            total = len(self.pedacos)
            inicio = max(0, desde_tk - self.tk_base)
            comandos = self.tk[inicio:]
            del self.tk[:inicio]
            self.tk_base += inicio
            total_tk = self.tk_base + len(self.tk)
        return {"pedacos": novos, "desde": total, "tk": comandos, "desde_tk": total_tk, "fim": terminou,
                "codigo": self.proc.returncode if terminou else None}

    def escrever(self, texto):
        try:
            self.proc.stdin.write(texto.encode("utf-8"))
            self.proc.stdin.flush()
        except (OSError, ValueError):
            pass

    def parar(self):
        if self.proc.poll() is None:
            try:
                self.proc.kill()
            except OSError:
                pass

    @classmethod
    def rodando(cls):
        return any(p.proc.poll() is None for p in cls.todos.values())

    @classmethod
    def limpar(cls):
        agora = time.time()
        for pid, p in list(cls.todos.items()):
            if p.proc.poll() is not None and agora - p.criado > 600:
                del cls.todos[pid]


class Atividade:
    ultima = time.time()

    @classmethod
    def tocar(cls):
        cls.ultima = time.time()


def baixar_libs():
    faltando = [a for a in ARQUIVOS_ACE if not (Config.libs() / a).exists()]
    if not faltando:
        return True
    registrar("Primeira execução: baixando o editor (só desta vez)...")
    for nome in faltando:
        destino = Config.libs() / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            pedido = urllib.request.Request(URL_ACE + nome, headers={"User-Agent": "PyCode"})
            with urllib.request.urlopen(pedido, timeout=30) as resposta:
                dados = resposta.read()
            temporario = destino.with_suffix(destino.suffix + ".tmp")
            temporario.write_bytes(dados)
            temporario.replace(destino)
            registrar(f"  ok {nome} ({len(dados) // 1024} KB)")
        except Exception as erro:
            registrar(f"  falhou {nome}: {erro}")
            return False
    return True


def info():
    return {
        "python": sys.version.split()[0],
        "pasta": str(Config.projetos()),
        "sistema": sys.platform,
        "abrir_pasta": sys.platform.startswith("win") or sys.platform == "darwin" or bool(shutil.which("xdg-open")),
        "vscode": bool(shutil.which("code")),
        "ace": all((Config.libs() / a).exists() for a in ARQUIVOS_ACE),
        "ponte_tk": usar_ponte(),
    }


def abrir_no_sistema(caminho):
    if sys.platform.startswith("win"):
        os.startfile(str(caminho))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(caminho)])
    else:
        subprocess.Popen(["xdg-open", str(caminho)])


class Manipulador(BaseHTTPRequestHandler):
    server_version = "PyCode"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return host in ("127.0.0.1", "localhost")

    def _enviar(self, status, corpo, tipo="application/json", extras=None):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        elif isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for chave, valor in (extras or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        self.wfile.write(corpo)

    def _erro(self, status, msg):
        self._enviar(status, {"erro": msg})

    def _corpo(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > 25_000_000:
            raise ErroUsuario("Arquivo grande demais.")
        return self.rfile.read(tamanho) if tamanho else b""

    def _json(self):
        bruto = self._corpo()
        try:
            return json.loads(bruto.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ErroUsuario("Pedido inválido.")

    def do_GET(self):
        Atividade.tocar()
        if not self._host_ok():
            return self._erro(403, "Acesso negado.")
        url = urlparse(self.path)
        consulta = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if url.path == "/api/exportar":
                return self._exportar(consulta)
            if url.path.startswith("/api/"):
                if self.headers.get("X-PyCode") != "1":
                    return self._erro(403, "Acesso negado.")
                return self._enviar(200, self._api_get(url.path, consulta))
            return self._estatico(url.path)
        except ErroUsuario as erro:
            self._erro(erro.status, str(erro))
        except Exception as erro:
            registrar(f"Erro GET {url.path}: {erro!r}")
            self._erro(500, "Erro interno do PyCode.")

    def do_POST(self):
        Atividade.tocar()
        if not self._host_ok() or self.headers.get("X-PyCode") != "1":
            return self._erro(403, "Acesso negado.")
        url = urlparse(self.path)
        consulta = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if url.path == "/api/importar":
                return self._enviar(200, self._importar(consulta.get("nome", "importado"), self._corpo()))
            return self._enviar(200, self._api_post(url.path, self._json()))
        except ErroUsuario as erro:
            self._erro(erro.status, str(erro))
        except Exception as erro:
            registrar(f"Erro POST {url.path}: {erro!r}")
            self._erro(500, "Erro interno do PyCode.")

    def _estatico(self, caminho):
        if caminho in ("/", "/index.html"):
            alvo = WEB / "index.html"
        elif caminho.startswith("/libs/ace/"):
            partes = caminho[len("/libs/ace/"):].split("/")
            if any(p in ("", ".", "..") for p in partes):
                return self._erro(404, "Não encontrado.")
            alvo = Config.libs().joinpath(*partes)
        else:
            nome = caminho.lstrip("/")
            if nome not in ("manifest.webmanifest", "sw.js", "icone-192.png", "icone-512.png", "icone.ico"):
                return self._erro(404, "Não encontrado.")
            alvo = WEB / nome
        if not alvo.is_file():
            return self._erro(404, "Não encontrado.")
        cache = "public, max-age=604800" if caminho.startswith("/libs/") else "no-cache"
        self._enviar(200, alvo.read_bytes(), TIPOS.get(alvo.suffix, "application/octet-stream"), {"Cache-Control": cache})

    def _api_get(self, rota, q):
        if rota == "/api/vivo":
            return {"app": "pycode"}
        if rota == "/api/info":
            return info()
        if rota == "/api/projetos":
            return {"projetos": listar_projetos()}
        if rota == "/api/projeto":
            pasta = pasta_projeto(q.get("nome"))
            return {"nome": pasta.name, "arquivos": ler_arquivos(pasta)}
        if rota == "/api/saida":
            processo = Processo.todos.get(q.get("id", ""))
            if not processo:
                raise ErroUsuario("Execução não encontrada.", 404)
            return processo.ler(int(q.get("desde", 0)), int(q.get("desde_tk", 0)))
        raise ErroUsuario("Rota desconhecida.", 404)

    def _api_post(self, rota, d):
        if rota == "/api/projeto/criar":
            nome = nome_livre(d.get("nome") or "projeto")
            pasta = pasta_projeto(nome, existir=False)
            pasta.mkdir(parents=True)
            (pasta / "main.py").write_text("", encoding="utf-8")
            return {"nome": nome}
        if rota == "/api/projeto/renomear":
            origem = pasta_projeto(d.get("nome"))
            destino = pasta_projeto(d.get("novo"), existir=False)
            if destino.exists():
                raise ErroUsuario("Já existe um projeto com esse nome.")
            origem.rename(destino)
            return {"nome": destino.name}
        if rota == "/api/projeto/excluir":
            pasta = pasta_projeto(d.get("nome"))
            mandar_lixeira(pasta, pasta.name)
            return {"ok": True}
        if rota == "/api/arquivo/salvar":
            caminho = caminho_arquivo(d.get("projeto"), d.get("nome"))
            conteudo = str(d.get("conteudo", ""))
            if len(conteudo.encode("utf-8")) > LIMITE_ARQUIVO:
                raise ErroUsuario("Arquivo grande demais (máximo 1 MB).")
            temporario = caminho.with_name(caminho.name + ".pycode-tmp")
            temporario.write_text(conteudo, encoding="utf-8", newline="")
            temporario.replace(caminho)
            return {"ok": True}
        if rota == "/api/arquivo/renomear":
            origem = caminho_arquivo(d.get("projeto"), d.get("nome"))
            destino = caminho_arquivo(d.get("projeto"), d.get("novo"))
            if destino.exists():
                raise ErroUsuario("Já existe um arquivo com esse nome.")
            if origem.exists():
                origem.rename(destino)
            return {"ok": True}
        if rota == "/api/arquivo/excluir":
            caminho = caminho_arquivo(d.get("projeto"), d.get("nome"))
            if caminho.exists():
                mandar_lixeira(caminho, f"{caminho.parent.name}-{caminho.name}")
            return {"ok": True}
        if rota == "/api/analisar":
            modulos = set()
            try:
                modulos = {p.stem for p in pasta_projeto(d.get("projeto")).glob("*.py")}
            except ErroUsuario:
                pass
            if usar_ponte():
                modulos.add("tkinter")
            return {"problemas": analisar(str(d.get("codigo", "")), str(d.get("nome", "main.py")), modulos)}
        if rota == "/api/rodar":
            caminho = caminho_arquivo(d.get("projeto"), d.get("arquivo"))
            if caminho.suffix.lower() != ".py" or not caminho.exists():
                raise ErroUsuario("Só arquivos .py salvos podem ser executados.")
            return {"id": Processo(caminho.name, caminho.parent).id}
        if rota == "/api/entrada":
            processo = Processo.todos.get(str(d.get("id", "")))
            if processo:
                processo.escrever(str(d.get("texto", "")))
            return {"ok": True}
        if rota == "/api/tk-evento":
            processo = Processo.todos.get(str(d.get("id", "")))
            if processo:
                eventos = d.get("eventos") if isinstance(d.get("eventos"), list) else [d]
                for evento in eventos:
                    processo.enviar_tk({"cid": str(evento.get("cid", "")), "dados": str(evento.get("dados", "{}"))})
            return {"ok": True}
        if rota == "/api/tk-resposta":
            processo = Processo.todos.get(str(d.get("id", "")))
            if processo:
                processo.enviar_tk({"resposta": d.get("pedido"), "valor": d.get("valor")})
            return {"ok": True}
        if rota == "/api/parar":
            processo = Processo.todos.get(str(d.get("id", "")))
            if processo:
                processo.parar()
            return {"ok": True}
        if rota == "/api/abrir-pasta":
            alvo = pasta_projeto(d["projeto"]) if d.get("projeto") else Config.projetos()
            abrir_no_sistema(alvo)
            return {"ok": True}
        if rota == "/api/abrir-vscode":
            codigo = shutil.which("code")
            if not codigo:
                raise ErroUsuario("VS Code não encontrado no PATH.")
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            subprocess.Popen([codigo, str(pasta_projeto(d.get("projeto")))], creationflags=flags)
            return {"ok": True}
        raise ErroUsuario("Rota desconhecida.", 404)

    def _importar(self, nome, dados):
        try:
            pacote = zipfile.ZipFile(io.BytesIO(dados))
        except zipfile.BadZipFile:
            raise ErroUsuario("Esse arquivo não é um .zip válido.")
        arquivos = {}
        for info_zip in pacote.infolist():
            if info_zip.is_dir() or "__MACOSX" in info_zip.filename or info_zip.file_size > LIMITE_ARQUIVO:
                continue
            base = re.sub(r"[^A-Za-z0-9_.\-]+", "_", info_zip.filename.replace("\\", "/").split("/")[-1])
            if not NOME_ARQUIVO.match(base) or base in arquivos:
                continue
            bruto = pacote.read(info_zip)
            try:
                arquivos[base] = bruto.decode("utf-8")
            except UnicodeDecodeError:
                arquivos[base] = bruto.decode("latin-1")
        if not arquivos:
            raise ErroUsuario("Nenhum arquivo de código encontrado no .zip.")
        base_nome = PROIBIDOS_PROJETO.sub("_", re.sub(r"\.zip$", "", str(nome), flags=re.I)).strip(" .") or "importado"
        destino = pasta_projeto(nome_livre(base_nome[:60]), existir=False)
        destino.mkdir(parents=True)
        for arquivo, conteudo in arquivos.items():
            (destino / arquivo).write_text(conteudo, encoding="utf-8", newline="")
        return {"nome": destino.name}

    def _exportar(self, q):
        pasta = pasta_projeto(q.get("nome"))
        memoria = io.BytesIO()
        with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as pacote:
            for nome, conteudo in ler_arquivos(pasta).items():
                pacote.writestr(f"{pasta.name}/{nome}", conteudo)
        nome_zip = f"{pasta.name}.zip"
        self._enviar(200, memoria.getvalue(), "application/zip",
                     {"Content-Disposition": f"attachment; filename=\"projeto.zip\"; filename*=UTF-8''{quote(nome_zip)}"})


def ja_rodando(porta):
    try:
        pedido = urllib.request.Request(f"http://127.0.0.1:{porta}/api/vivo", headers={"X-PyCode": "1"})
        with urllib.request.urlopen(pedido, timeout=1.5) as resposta:
            return json.loads(resposta.read()).get("app") == "pycode"
    except Exception:
        return False


def abrir_janela(url):
    candidatos = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidatos += [Path(base) / "Microsoft/Edge/Application/msedge.exe", Path(base) / "Google/Chrome/Application/chrome.exe"]
    else:
        for nome in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            achado = shutil.which(nome)
            if achado:
                candidatos.append(Path(achado))
    for exe in candidatos:
        if exe.exists():
            subprocess.Popen([str(exe), f"--app={url}", "--window-size=1280,820"])
            return
    if shutil.which("termux-open-url"):
        subprocess.Popen(["termux-open-url", url])
        return
    try:
        webbrowser.open(url)
    except Exception:
        pass


def vigiar(servidor, limite):
    while True:
        time.sleep(15)
        if time.time() - Atividade.ultima > limite and not Processo.rodando():
            registrar("Sem uso por um tempo. Encerrando o PyCode.")
            servidor.shutdown()
            return


def instalar_atalho():
    if os.name != "nt":
        print("O atalho automático é só para Windows.")
        return
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    alvo = pythonw if pythonw.exists() else Path(sys.executable)
    lancador = APP / "PyCode.pyw"
    icone = WEB / "icone.ico"
    aspas = lambda caminho: str(caminho).replace("'", "''")
    comando = (
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([IO.Path]::Combine($d,'PyCode.lnk'));"
        f"$s.TargetPath='{aspas(alvo)}';$s.Arguments='\"{aspas(lancador)}\"';"
        f"$s.WorkingDirectory='{aspas(APP)}';$s.IconLocation='{aspas(icone)}';$s.Description='PyCode';$s.Save()"
    )
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando], check=True)
    print("Atalho 'PyCode' criado na área de trabalho.")


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="PyCode — editor Python local")
    parser.add_argument("--janela", action="store_true", help="abre em janela de app e fecha sozinho quando a janela fecha")
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--pasta", help="onde guardar os projetos (padrão: ~/PyCode)")
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o navegador")
    parser.add_argument("--instalar", action="store_true", help="cria atalho na área de trabalho (Windows)")
    parser.add_argument("--auto-fechar", type=int, default=0, metavar="MIN", help="encerra após MIN minutos sem uso")
    parser.add_argument("--baixar", action="store_true", help="só baixa o editor e sai")
    parser.add_argument("--wake-lock", action="store_true", help="no Termux, mantém o aparelho acordado enquanto roda")
    args = parser.parse_args(argumentos)
    if args.pasta:
        Config.base = Path(args.pasta).expanduser()
    if args.instalar:
        instalar_atalho()
        return
    if args.baixar:
        sys.exit(0 if baixar_libs() else 1)
    Config.projetos().mkdir(parents=True, exist_ok=True)
    if not any(p.is_dir() for p in Config.projetos().iterdir()):
        (Config.projetos() / "treino").mkdir()
        (Config.projetos() / "treino" / "main.py").write_text("", encoding="utf-8")
    url = f"http://127.0.0.1:{args.porta}/"
    if ja_rodando(args.porta):
        if not args.sem_navegador:
            abrir_janela(url)
        return
    baixar_libs()
    if args.wake_lock and shutil.which("termux-wake-lock"):
        subprocess.run(["termux-wake-lock"], check=False)
    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), Manipulador)
    servidor.daemon_threads = True
    registrar(f"PyCode rodando em {url}  (projetos em {Config.projetos()})")
    limite = 180 if args.janela else args.auto_fechar * 60
    if limite:
        threading.Thread(target=vigiar, args=(servidor, limite), daemon=True).start()
    if not args.sem_navegador:
        threading.Timer(0.4, lambda: abrir_janela(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for processo in Processo.todos.values():
            processo.parar()
        servidor.server_close()
        if args.wake_lock and shutil.which("termux-wake-unlock"):
            subprocess.run(["termux-wake-unlock"], check=False)


if __name__ == "__main__":
    main()
