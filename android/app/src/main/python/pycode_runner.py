import builtins
import io
import json
import os
import re
import socket
import sys
import threading
import traceback

_mantidos = []
_trava_envio = threading.Lock()


def _registrar_erro(caminho, texto):
    if not caminho:
        return
    try:
        with open(caminho, "a", encoding="utf-8") as arquivo:
            arquivo.write(texto + "\n")
    except OSError:
        pass


def _conectar(porta, token, canal):
    sock = socket.create_connection(("127.0.0.1", porta), timeout=10)
    sock.settimeout(None)
    sock.sendall((json.dumps({"canal": canal, "token": token, "pid": os.getpid()}) + "\n").encode("utf-8"))
    _mantidos.append(sock)
    return sock


def _enviar(sock, quadro):
    dados = (json.dumps(quadro, ensure_ascii=False) + "\n").encode("utf-8")
    with _trava_envio:
        sock.sendall(dados)


class Saida(io.TextIOBase):
    encoding = "utf-8"
    errors = "replace"

    def __init__(self, sock, tipo):
        self._sock = sock
        self._tipo = tipo

    def writable(self):
        return True

    def isatty(self):
        return False

    def write(self, texto):
        if not isinstance(texto, str):
            texto = str(texto)
        if texto:
            try:
                _enviar(self._sock, {"t": self._tipo, "d": texto})
            except OSError:
                os._exit(137)
        return len(texto)

    def flush(self):
        pass


class Entrada(io.TextIOBase):
    encoding = "utf-8"
    errors = "replace"

    def __init__(self):
        self._buffer = ""
        self._acabou = False
        self._condicao = threading.Condition()

    def readable(self):
        return True

    def isatty(self):
        return False

    def alimentar(self, texto):
        with self._condicao:
            self._buffer += texto
            self._condicao.notify_all()

    def encerrar(self):
        with self._condicao:
            self._acabou = True
            self._condicao.notify_all()

    def readline(self, limite=-1):
        with self._condicao:
            while "\n" not in self._buffer and not self._acabou:
                self._condicao.wait()
            posicao = self._buffer.find("\n")
            if posicao < 0:
                linha, self._buffer = self._buffer, ""
            else:
                linha, self._buffer = self._buffer[: posicao + 1], self._buffer[posicao + 1:]
            return linha

    def read(self, tamanho=-1):
        with self._condicao:
            while not self._acabou and (tamanho < 0 or len(self._buffer) < tamanho):
                self._condicao.wait()
            if tamanho < 0:
                texto, self._buffer = self._buffer, ""
            else:
                texto, self._buffer = self._buffer[:tamanho], self._buffer[tamanho:]
            return texto

    def __iter__(self):
        return self

    def __next__(self):
        linha = self.readline()
        if not linha:
            raise StopIteration
        return linha


def _ler_principal(sock, entrada):
    try:
        for linha in sock.makefile("rb"):
            try:
                quadro = json.loads(linha.decode("utf-8"))
            except ValueError:
                continue
            if quadro.get("t") == "in":
                entrada.alimentar(str(quadro.get("d", "")))
    except OSError:
        pass
    entrada.encerrar()
    os._exit(137)


def _usa_tkinter(fonte):
    return re.search(r"^\s*(?:from\s+tkinter\b|import\s+tkinter\b)", fonte, re.M) is not None


def _imprimir_erro(tipo, erro, tb, arquivo):
    if isinstance(erro, SyntaxError):
        texto = "".join(traceback.format_exception_only(tipo, erro))
        sys.stderr.write(texto)
        return
    while tb is not None and tb.tb_frame.f_code.co_filename != arquivo:
        tb = tb.tb_next
    sys.stderr.write("".join(traceback.format_exception(tipo, erro, tb)))


def _esperar_threads():
    atual = threading.current_thread()
    while True:
        pendentes = [t for t in threading.enumerate() if t is not atual and not t.daemon and t.is_alive()]
        if not pendentes:
            return
        for t in pendentes:
            t.join()


def _rodar(porta, token, pasta, arquivo, erro_arquivo):
    principal = _conectar(porta, token, "main")
    caminho = os.path.join(pasta, arquivo)
    with open(caminho, encoding="utf-8") as origem:
        fonte = origem.read()
    if _usa_tkinter(fonte):
        tk = _conectar(porta, token, "tk")
        os.environ["PYCODE_TK_OUT"] = str(tk.fileno())
        os.environ["PYCODE_TK_IN"] = str(tk.fileno())
    entrada = Entrada()
    threading.Thread(target=_ler_principal, args=(principal, entrada), daemon=True).start()
    sys.stdout = Saida(principal, "out")
    sys.stderr = Saida(principal, "err")
    sys.stdin = entrada
    os.chdir(pasta)
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    codigo = 0
    ambiente = {"__name__": "__main__", "__file__": caminho, "__builtins__": builtins}
    try:
        exec(compile(fonte, arquivo, "exec"), ambiente)
    except SystemExit as saida:
        alvo = saida.code
        if alvo is None:
            codigo = 0
        elif isinstance(alvo, int):
            codigo = alvo
        else:
            sys.stderr.write(str(alvo) + "\n")
            codigo = 1
    except BaseException:
        tipo, erro, tb = sys.exc_info()
        _imprimir_erro(tipo, erro, tb, arquivo)
        codigo = 1
    try:
        _esperar_threads()
    except BaseException:
        pass
    _enviar(principal, {"t": "fim", "codigo": codigo})
    try:
        principal.shutdown(socket.SHUT_WR)
    except OSError:
        pass


def executar(porta, token, pasta, arquivo, erro_arquivo=None):
    try:
        _rodar(int(porta), str(token), str(pasta), str(arquivo), erro_arquivo)
    except BaseException:
        _registrar_erro(erro_arquivo, traceback.format_exc())
        raise
