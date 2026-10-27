import hmac
import json
import os
import secrets
import signal
import socket
import tempfile
import threading
import time
import uuid

import pycode_servidor as servidor

TEMPO_PARTIDA = float(os.environ.get("PYCODE_TEMPO_PARTIDA", "20"))


def lancar_android(porta, token, pasta, arquivo, erro_arquivo):
    from java import jclass

    jclass("io.github.itallomendes124.pycode.Lancador").iniciar(porta, token, str(pasta), arquivo, erro_arquivo)


class _ProcRemoto:
    def __init__(self, dono):
        self._dono = dono

    @property
    def returncode(self):
        return self._dono.codigo

    def poll(self):
        return self._dono.codigo if self._dono.fim.is_set() else None

    def kill(self):
        self._dono.parar()


class ProcessoRemoto(servidor.Processo):
    lancador = staticmethod(lancar_android)

    def __init__(self, arquivo, pasta):
        self.id = uuid.uuid4().hex[:12]
        self.pedacos = []
        self.tamanho = 0
        self.trava = threading.Lock()
        self.criado = time.time()
        self.tk = []
        self.tk_base = 0
        self.fd_eventos = None
        self.token = secrets.token_hex(16)
        self.canais = {}
        self.pid = None
        self.codigo = None
        self.fim = threading.Event()
        self._envio = threading.Lock()
        self.proc = _ProcRemoto(self)
        self.leitores = []
        self.erro_arquivo = os.path.join(tempfile.gettempdir(), f"pycode-executor-{self.id}.erro")
        self.escuta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.escuta.bind(("127.0.0.1", 0))
        self.escuta.listen(4)
        self.porta = self.escuta.getsockname()[1]
        aceitador = threading.Thread(target=self._aceitar, daemon=True)
        self.leitores.append(aceitador)
        aceitador.start()
        servidor.Processo.todos[self.id] = self
        servidor.Processo.limpar()
        try:
            type(self).lancador(self.porta, self.token, str(pasta), arquivo, self.erro_arquivo)
        except Exception as erro:
            self._anexar("err", f"Não consegui iniciar a execução: {erro}\n")
            self._terminar(1)

    def _terminar(self, codigo):
        if self.codigo is None:
            self.codigo = codigo
        self.fim.set()
        try:
            self.escuta.close()
        except OSError:
            pass

    def _falha_de_partida(self):
        detalhe = ""
        try:
            with open(self.erro_arquivo, encoding="utf-8") as arquivo:
                detalhe = arquivo.read().strip()
        except OSError:
            pass
        mensagem = "O processo que executa o código não iniciou (tempo esgotado)."
        if detalhe:
            mensagem += "\n" + detalhe[-1500:]
        self._anexar("err", mensagem + "\n")
        self._terminar(1)

    def _aceitar(self):
        self.escuta.settimeout(1.0)
        inicio = time.time()
        while not self.fim.is_set():
            try:
                sock, _ = self.escuta.accept()
            except socket.timeout:
                if "main" not in self.canais and time.time() - inicio > TEMPO_PARTIDA:
                    self._falha_de_partida()
                    return
                continue
            except OSError:
                return
            leitor = threading.Thread(target=self._atender, args=(sock,), daemon=True)
            with self.trava:
                self.leitores.append(leitor)
            leitor.start()

    def _atender(self, sock):
        try:
            sock.settimeout(5)
            arquivo = sock.makefile("rb")
            linha = arquivo.readline()
            hello = json.loads(linha.decode("utf-8"))
            if not hmac.compare_digest(str(hello.get("token", "")), self.token):
                sock.close()
                return
            sock.settimeout(None)
        except (OSError, ValueError):
            try:
                sock.close()
            except OSError:
                pass
            return
        canal = hello.get("canal")
        if canal == "main" and "main" not in self.canais:
            self.pid = hello.get("pid")
            self.canais["main"] = sock
            self._ler_principal(arquivo)
        elif canal == "tk" and "tk" not in self.canais:
            self.canais["tk"] = sock
            self._ler_tk_socket(arquivo)
        else:
            sock.close()

    def _ler_principal(self, arquivo):
        try:
            for linha in arquivo:
                try:
                    quadro = json.loads(linha.decode("utf-8"))
                except ValueError:
                    continue
                tipo = quadro.get("t")
                if tipo in ("out", "err"):
                    self._anexar(tipo, str(quadro.get("d", "")))
                elif tipo == "fim":
                    self.codigo = int(quadro.get("codigo", 0))
        except (OSError, ValueError):
            pass
        self._terminar(-9)
        self._fechar_canais()

    def _ler_tk_socket(self, arquivo):
        try:
            for linha in arquivo:
                try:
                    comando = json.loads(linha.decode("utf-8"))
                except ValueError:
                    continue
                with self.trava:
                    self.tk.append(comando)
        except (OSError, ValueError):
            pass

    def _fechar_canais(self):
        for sock in list(self.canais.values()):
            try:
                sock.close()
            except OSError:
                pass

    def _enviar(self, canal, quadro):
        sock = self.canais.get(canal)
        if sock is None:
            return
        dados = (json.dumps(quadro, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            with self._envio:
                sock.sendall(dados)
        except OSError:
            pass

    def enviar_tk(self, mensagem):
        self._enviar("tk", mensagem)

    def escrever(self, texto):
        self._enviar("main", {"t": "in", "d": texto})

    def parar(self):
        if self.fim.is_set():
            return
        if self.pid:
            try:
                os.kill(int(self.pid), signal.SIGKILL)
            except (OSError, ValueError):
                pass
        self._terminar(-9)
        self._fechar_canais()


def instalar(lancador=None):
    if lancador is not None:
        ProcessoRemoto.lancador = staticmethod(lancador)
    servidor.Processo = ProcessoRemoto
