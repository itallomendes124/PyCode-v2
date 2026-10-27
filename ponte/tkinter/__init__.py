import json
import sys
import traceback

try:
    from browser import window
except ImportError:
    window = None


class _Ponte:
    def __init__(self):
        import os
        import select
        self._os = os
        self._select = select
        try:
            self._fd_saida = int(os.environ["PYCODE_TK_OUT"])
            self._fd_entrada = int(os.environ["PYCODE_TK_IN"])
        except (KeyError, ValueError):
            raise ImportError("Este tkinter só funciona dentro do PyCode.")
        self._buffer = b""
        self._pendentes = []
        self._pedido = 0

    def _enviar(self, mensagem):
        dados = (json.dumps(mensagem) + "\n").encode("utf-8")
        while dados:
            escrito = self._os.write(self._fd_saida, dados)
            dados = dados[escrito:]

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        if nome in ("medida", "confirmar", "perguntarTexto"):
            return lambda *args: self._pedir(nome, args)
        return lambda *args: self._enviar({"m": nome, "a": list(args)})

    def _linha(self, espera):
        while b"\n" not in self._buffer:
            prontos, _, _ = self._select.select([self._fd_entrada], [], [], espera)
            if not prontos:
                return None
            bloco = self._os.read(self._fd_entrada, 65536)
            if not bloco:
                return {"fim": True}
            self._buffer += bloco
            if self._buffer:
                espera = None
        linha, self._buffer = self._buffer.split(b"\n", 1)
        return json.loads(linha.decode("utf-8"))

    def _pedir(self, nome, args):
        self._pedido += 1
        numero = self._pedido
        self._enviar({"m": nome, "a": list(args), "pedido": numero})
        while True:
            mensagem = self._linha(None)
            if mensagem.get("fim"):
                raise SystemExit(0)
            if mensagem.get("resposta") == numero:
                return mensagem.get("valor")
            self._pendentes.append(mensagem)

    def proximo(self, espera):
        if self._pendentes:
            return self._pendentes.pop(0)
        return self._linha(espera)


_NAVEGADOR = window is not None
TK = window.TK if _NAVEGADOR else _Ponte()

END = "end"
INSERT = "insert"
LEFT, RIGHT, TOP, BOTTOM = "left", "right", "top", "bottom"
X, Y, BOTH, NONE = "x", "y", "both", "none"
N, S, E, W = "n", "s", "e", "w"
NW, NE, SW, SE, CENTER = "nw", "ne", "sw", "se", "center"
NS, EW, NSEW = "ns", "ew", "nsew"
NORMAL, DISABLED, ACTIVE, HIDDEN = "normal", "disabled", "active", "hidden"
RAISED, SUNKEN, FLAT, RIDGE, GROOVE, SOLID = "raised", "sunken", "flat", "ridge", "groove", "solid"
HORIZONTAL, VERTICAL = "horizontal", "vertical"
WORD, CHAR = "word", "char"
YES, NO, TRUE, FALSE = True, False, True, False
ALL = "all"


class TclError(Exception):
    pass


_contador = [0]
_callbacks = {}
_widgets = {}
_raizes = []
_timers = []
_timers_ativos = set()
_sair = [False]


def _novo(prefixo):
    _contador[0] += 1
    return f"{prefixo}{_contador[0]}"


def _registrar(funcao):
    cid = _novo("c")
    _callbacks[cid] = funcao
    return cid


def _par(valor):
    if isinstance(valor, (list, tuple)):
        return [int(valor[0]), int(valor[1] if len(valor) > 1 else valor[0])]
    return [int(valor or 0), int(valor or 0)]


def _serializar(valor):
    if isinstance(valor, (list, tuple)):
        return [_serializar(v) for v in valor]
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    return str(valor)


class Event:
    def __init__(self, dados):
        self.type = dados.get("type", "")
        self.char = dados.get("char", "")
        self.keysym = dados.get("keysym", "")
        self.keycode = dados.get("keycode", 0)
        self.state = dados.get("state", 0)
        self.x = dados.get("x", 0)
        self.y = dados.get("y", 0)
        self.x_root = dados.get("x_root", 0)
        self.y_root = dados.get("y_root", 0)
        self.num = dados.get("num", 0)
        self.delta = dados.get("delta", 0)
        self.width = dados.get("width", 0)
        self.height = dados.get("height", 0)
        self.widget = _widgets.get(dados.get("widget"))

    def __repr__(self):
        return f"<Event {self.type} keysym={self.keysym!r} char={self.char!r} x={self.x} y={self.y}>"


def _chamar(cid, dados_json=None):
    funcao = _callbacks.get(str(cid))
    if funcao is None:
        return None
    try:
        dados = json.loads(str(dados_json)) if dados_json else {}
    except ValueError:
        dados = {}
    try:
        if dados.get("_interno"):
            resultado = funcao(dados)
        elif dados.get("_sem_evento"):
            resultado = funcao()
        else:
            resultado = funcao(Event(dados))
    except Exception:
        traceback.print_exc()
        return None
    return "break" if resultado == "break" else None


if _NAVEGADOR:
    window.tkChamar = _chamar


def _agendar(ms, cid):
    if _NAVEGADOR:
        TK.after(int(ms), cid)
        return
    import heapq
    import time
    _contador[0] += 1
    _timers_ativos.add(cid)
    heapq.heappush(_timers, (time.monotonic() + max(0, int(ms)) / 1000, _contador[0], cid))


def _cancelar(cid):
    if _NAVEGADOR:
        TK.cancelarAfter(cid)
    else:
        _timers_ativos.discard(cid)


def _processar(bloquear):
    import heapq
    import time
    while True:
        while _timers and _timers[0][0] <= time.monotonic():
            _, _, cid = heapq.heappop(_timers)
            if cid in _timers_ativos:
                _timers_ativos.discard(cid)
                _chamar(cid, '{"_sem_evento": 1}')
        if bloquear and (not _raizes or _sair[0]):
            return
        if bloquear:
            espera = max(0.0, _timers[0][0] - time.monotonic()) if _timers else None
        else:
            espera = 0
        mensagem = TK.proximo(espera)
        if mensagem is None:
            if not bloquear:
                return
            continue
        if mensagem.get("fim"):
            raise SystemExit(0)
        if "cid" in mensagem:
            _chamar(mensagem["cid"], mensagem.get("dados"))


class Variable:
    _padrao = ""

    def __init__(self, master=None, value=None, name=None):
        self._valor = self._padrao if value is None else value
        self._ligados = []
        self._traces = {}

    def _converter(self, valor):
        return valor

    def get(self):
        return self._converter(self._valor)

    def _avisar(self, origem=None):
        for widget in list(self._ligados):
            if widget is not origem:
                widget._var_mudou(self)
        for funcao in list(self._traces.values()):
            funcao(str(self), "", "write")

    def set(self, valor):
        self._valor = valor
        self._avisar()

    def _definir_de(self, origem, valor):
        self._valor = valor
        self._avisar(origem)

    def trace_add(self, modo, funcao):
        nome = _novo("t")
        self._traces[nome] = funcao
        return nome

    def trace(self, modo, funcao):
        return self.trace_add(modo, funcao)

    trace_variable = trace

    def trace_remove(self, modo, nome):
        self._traces.pop(nome, None)

    def trace_vdelete(self, modo, nome):
        self._traces.pop(nome, None)

    def __str__(self):
        return f"PY_VAR{id(self)}"


class StringVar(Variable):
    _padrao = ""

    def _converter(self, valor):
        return str(valor)


class IntVar(Variable):
    _padrao = 0

    def _converter(self, valor):
        try:
            return int(float(valor))
        except (TypeError, ValueError):
            raise TclError(f'expected integer but got "{valor}"')


class DoubleVar(Variable):
    _padrao = 0.0

    def _converter(self, valor):
        try:
            return float(valor)
        except (TypeError, ValueError):
            raise TclError(f'expected floating-point number but got "{valor}"')


class BooleanVar(Variable):
    _padrao = False

    def _converter(self, valor):
        if isinstance(valor, str):
            return valor.strip().lower() in ("1", "true", "yes", "sim")
        return bool(valor)


class Misc:
    master = None
    _id = None

    def _iniciar_base(self):
        self._opcoes = {}
        self._var = None
        self.children = {}
        _widgets[self._id] = self

    def after(self, ms, funcao=None, *args):
        if funcao is None:
            return None
        cid = _registrar(lambda: funcao(*args))
        _agendar(ms, cid)
        return cid

    def after_idle(self, funcao, *args):
        return self.after(0, funcao, *args)

    def after_cancel(self, cid):
        _cancelar(str(cid))
        _callbacks.pop(str(cid), None)

    def bind(self, sequencia=None, funcao=None, add=None):
        if funcao is None:
            return None
        cid = _registrar(funcao)
        TK.bind(self._id, str(sequencia), cid)
        return cid

    def bind_all(self, sequencia=None, funcao=None, add=None):
        return self._raiz().bind(sequencia, funcao, add)

    def unbind(self, sequencia, funcid=None):
        TK.unbind(self._id, str(sequencia))

    def focus_set(self):
        TK.focar(self._id)

    focus = focus_set
    focus_force = focus_set

    def update(self):
        if not _NAVEGADOR:
            _processar(False)

    def update_idletasks(self):
        if not _NAVEGADOR:
            _processar(False)

    def winfo_width(self):
        return int(TK.medida(self._id, "w") or 1)

    def winfo_height(self):
        return int(TK.medida(self._id, "h") or 1)

    winfo_reqwidth = winfo_width
    winfo_reqheight = winfo_height

    def winfo_screenwidth(self):
        return int(TK.medida("tela", "w") or 1024)

    def winfo_screenheight(self):
        return int(TK.medida("tela", "h") or 768)

    def winfo_exists(self):
        return 1 if self._id in _widgets else 0

    def winfo_children(self):
        return [w for w in list(_widgets.values()) if w.master is self]

    def winfo_toplevel(self):
        return self._raiz()

    def _raiz(self):
        atual = self
        while atual.master is not None:
            atual = atual.master
        return atual

    def _peso(self, eixo, indice, weight, minsize):
        indices = indice if isinstance(indice, (list, tuple)) else [indice]
        for i in indices:
            TK.pesoGrid(self._id, eixo, int(i), float(weight or 0), int(minsize or 0))

    def columnconfigure(self, indice, cnf=None, weight=0, minsize=0, **kw):
        self._peso("col", indice, weight, minsize)

    def rowconfigure(self, indice, cnf=None, weight=0, minsize=0, **kw):
        self._peso("lin", indice, weight, minsize)

    grid_columnconfigure = columnconfigure
    grid_rowconfigure = rowconfigure

    def grid_propagate(self, flag=None):
        pass

    pack_propagate = grid_propagate

    def _texto_da_var(self):
        return {"text": str(self._var.get())}

    def _var_mudou(self, var):
        TK.configurar(self._id, json.dumps(self._texto_da_var()))

    def _ligar(self, var):
        if self._var is not None and self in self._var._ligados:
            self._var._ligados.remove(self)
        self._var = var
        var._ligados.append(self)

    def configure(self, cnf=None, **opcoes):
        if cnf:
            opcoes = {**cnf, **opcoes}
        if not opcoes:
            return dict(self._opcoes)
        envio = {}
        for chave, valor in opcoes.items():
            self._opcoes[chave] = valor
            if chave == "command":
                envio["command"] = _registrar(valor) if callable(valor) else None
            elif chave == "textvariable":
                if isinstance(valor, Variable):
                    self._ligar(valor)
                    envio.update(self._texto_da_var())
            elif chave == "text":
                envio["text"] = str(valor)
            else:
                envio[chave] = _serializar(valor)
        TK.configurar(self._id, json.dumps(envio))
        return None

    config = configure

    def cget(self, chave):
        return self._opcoes.get(chave, "")

    def __getitem__(self, chave):
        return self.cget(chave)

    def __setitem__(self, chave, valor):
        self.configure(**{chave: valor})

    def destroy(self):
        for filho in self.winfo_children():
            filho.destroy()
        if self in _raizes:
            _raizes.remove(self)
        if self._id in _widgets:
            del _widgets[self._id]
            TK.destruir(self._id)

    def quit(self):
        _sair[0] = True

    def mainloop(self, n=0):
        if _NAVEGADOR:
            return
        _sair[0] = False
        _processar(True)


class Tk(Misc):
    def __init__(self, screenName=None, baseName=None, className="Tk", useTk=True, **kw):
        self.master = None
        self._id = _novo("w")
        self._iniciar_base()
        self._titulo = "tk"
        _raizes.append(self)
        TK.novaJanela(self._id, "tk")
        TK.aoFechar(self._id, _registrar(self.destroy))
        self.tk = self

    def title(self, texto=None):
        if texto is None:
            return self._titulo
        self._titulo = str(texto)
        TK.titulo(self._id, self._titulo)
        return None

    wm_title = title

    def geometry(self, texto=None):
        if not texto:
            return f"{self.winfo_width()}x{self.winfo_height()}"
        tamanho = str(texto).split("+")[0].split("-")[0]
        if "x" in tamanho:
            largura, altura = tamanho.split("x", 1)
            TK.tamanho(self._id, int(largura), int(altura))
        return None

    wm_geometry = geometry

    def protocol(self, nome=None, funcao=None):
        if nome == "WM_DELETE_WINDOW" and funcao is not None:
            TK.aoFechar(self._id, _registrar(funcao))

    wm_protocol = protocol

    def resizable(self, *args, **kw):
        pass

    def minsize(self, *args):
        pass

    def maxsize(self, *args):
        pass

    def iconbitmap(self, *args, **kw):
        pass

    def iconphoto(self, *args, **kw):
        pass

    def attributes(self, *args, **kw):
        pass

    wm_attributes = attributes

    def overrideredirect(self, *args):
        pass

    def state(self, *args):
        return "normal"

    def withdraw(self):
        pass

    def deiconify(self):
        pass

    def lift(self, *args):
        pass

    def lower(self, *args):
        pass


class Toplevel(Tk):
    def __init__(self, master=None, cnf=None, **opcoes):
        super().__init__()
        self._mestre = master
        dados = dict(cnf or {})
        dados.update(opcoes)
        if dados:
            self.configure(**dados)


def _raiz_padrao():
    return _raizes[0] if _raizes else Tk()


def mainloop(n=0):
    _raiz_padrao().mainloop(n)


class Widget(Misc):
    _tipo = "frame"

    def __init__(self, master=None, cnf=None, **opcoes):
        if master is None:
            master = _raiz_padrao()
        self.master = master
        self._id = _novo("w")
        self._iniciar_base()
        TK.criar(self._id, self._tipo, master._id)
        dados = dict(cnf or {})
        dados.update(opcoes)
        dados.pop("name", None)
        self._preparar()
        if dados:
            self.configure(**dados)

    def _preparar(self):
        pass

    def grid(self, cnf=None, **opcoes):
        o = dict(cnf or {})
        o.update(opcoes)
        pai = self.master
        linha = o.get("row")
        if linha is None:
            linha = getattr(pai, "_proxima_linha", 0)
        linha = int(linha)
        rowspan = int(o.get("rowspan", 1))
        pai._proxima_linha = max(getattr(pai, "_proxima_linha", 0), linha + rowspan)
        sticky = o.get("sticky", "")
        if isinstance(sticky, (list, tuple)):
            sticky = "".join(sticky)
        envio = {
            "row": linha,
            "column": int(o.get("column", 0)),
            "rowspan": rowspan,
            "columnspan": int(o.get("columnspan", 1)),
            "sticky": str(sticky),
            "padx": _par(o.get("padx", 0)),
            "pady": _par(o.get("pady", 0)),
            "ipadx": int(o.get("ipadx", 0)),
            "ipady": int(o.get("ipady", 0)),
        }
        TK.grid(self._id, json.dumps(envio))

    grid_configure = grid

    def grid_forget(self):
        TK.esconder(self._id)

    grid_remove = grid_forget

    def pack(self, cnf=None, **opcoes):
        o = dict(cnf or {})
        o.update(opcoes)
        envio = {
            "side": str(o.get("side", "top")),
            "fill": str(o.get("fill", "none")),
            "expand": bool(o.get("expand", False)),
            "padx": _par(o.get("padx", 0)),
            "pady": _par(o.get("pady", 0)),
            "anchor": str(o.get("anchor", "center")),
        }
        TK.pack(self._id, json.dumps(envio))

    pack_configure = pack

    def pack_forget(self):
        TK.esconder(self._id)

    def place(self, cnf=None, **opcoes):
        o = dict(cnf or {})
        o.update(opcoes)
        envio = {k: _serializar(v) for k, v in o.items() if k in ("x", "y", "relx", "rely", "anchor", "width", "height", "relwidth", "relheight")}
        TK.place(self._id, json.dumps(envio))

    place_configure = place

    def place_forget(self):
        TK.esconder(self._id)


class Frame(Widget):
    _tipo = "frame"


class LabelFrame(Frame):
    pass


class Label(Widget):
    _tipo = "label"


class Message(Label):
    pass


class Button(Widget):
    _tipo = "button"

    def invoke(self):
        funcao = self._opcoes.get("command")
        return funcao() if callable(funcao) else None

    def flash(self):
        pass


class Entry(Widget):
    _tipo = "entry"

    def _preparar(self):
        self._texto = ""
        TK.aoMudar(self._id, _registrar(self._mudou))

    def _texto_da_var(self):
        self._texto = str(self._var.get())
        return {"value": self._texto}

    def _mudou(self, dados):
        self._texto = str(dados.get("valor", ""))
        if self._var is not None:
            self._var._definir_de(self, self._texto)

    def _definir(self, texto):
        self._texto = texto
        if self._var is not None:
            self._var._definir_de(self, texto)
        TK.configurar(self._id, json.dumps({"value": texto}))

    def _indice(self, indice):
        if indice in (END, INSERT):
            return len(self._texto)
        return max(0, min(int(indice), len(self._texto)))

    def get(self):
        return self._texto

    def insert(self, indice, texto):
        pos = self._indice(indice)
        self._definir(self._texto[:pos] + str(texto) + self._texto[pos:])

    def delete(self, primeiro, ultimo=None):
        a = self._indice(primeiro)
        b = a + 1 if ultimo is None else self._indice(ultimo)
        self._definir(self._texto[:a] + self._texto[b:])

    def icursor(self, indice):
        pass

    def select_range(self, *args):
        pass

    def selection_clear(self):
        pass


class Text(Widget):
    _tipo = "text"

    def _preparar(self):
        self._texto = ""
        TK.aoMudar(self._id, _registrar(self._mudou))

    def _mudou(self, dados):
        self._texto = str(dados.get("valor", ""))

    def _pos(self, indice):
        indice = str(indice)
        if indice.startswith("end") or indice.startswith("insert"):
            return len(self._texto)
        if "." not in indice:
            return len(self._texto)
        linha, coluna = indice.split(".", 1)
        linhas = self._texto.split("\n")
        posicao_linha = max(1, int(linha)) - 1
        if posicao_linha >= len(linhas):
            return len(self._texto)
        base = sum(len(x) + 1 for x in linhas[:posicao_linha])
        if coluna.startswith("end"):
            return base + len(linhas[posicao_linha])
        return base + min(int(coluna), len(linhas[posicao_linha]))

    def _enviar(self):
        TK.configurar(self._id, json.dumps({"value": self._texto}))
        TK.rolarFim(self._id)

    def insert(self, indice, texto, *tags):
        pos = self._pos(indice)
        self._texto = self._texto[:pos] + str(texto) + self._texto[pos:]
        self._enviar()

    def delete(self, primeiro, ultimo=None):
        a = self._pos(primeiro)
        b = a + 1 if ultimo is None else self._pos(ultimo)
        self._texto = self._texto[:a] + self._texto[b:]
        self._enviar()

    def get(self, primeiro="1.0", ultimo=END):
        a = self._pos(primeiro)
        if str(ultimo).startswith("end"):
            return self._texto[a:] + "\n"
        return self._texto[a:self._pos(ultimo)]

    def see(self, indice):
        pass

    def tag_configure(self, *args, **kw):
        pass

    tag_config = tag_configure


class Listbox(Widget):
    _tipo = "listbox"

    def _preparar(self):
        self._itens = []
        self._sel = []
        TK.aoMudar(self._id, _registrar(self._selecionou))

    def _selecionou(self, dados):
        try:
            self._sel = sorted(int(i) for i in json.loads(str(dados.get("valor", "[]"))))
        except (TypeError, ValueError):
            self._sel = []

    def _enviar(self):
        TK.listaDefinir(self._id, json.dumps(self._itens, ensure_ascii=False), json.dumps(self._sel))

    def _pos(self, indice, inserir=False):
        if indice == END:
            return len(self._itens) if inserir else len(self._itens) - 1
        if indice in ("active", "anchor"):
            return self._sel[0] if self._sel else 0
        return int(indice)

    def insert(self, indice, *itens):
        pos = max(0, min(self._pos(indice, True), len(self._itens)))
        novos = [str(i) for i in itens]
        self._itens[pos:pos] = novos
        self._sel = [i + len(novos) if i >= pos else i for i in self._sel]
        self._enviar()

    def delete(self, primeiro, ultimo=None):
        a = max(0, self._pos(primeiro))
        b = a if ultimo is None else self._pos(ultimo)
        b = min(b, len(self._itens) - 1)
        if b < a:
            return
        quantos = b - a + 1
        del self._itens[a:b + 1]
        self._sel = [i - quantos if i > b else i for i in self._sel if not a <= i <= b]
        self._enviar()

    def get(self, primeiro, ultimo=None):
        a = self._pos(primeiro)
        if ultimo is None:
            return self._itens[a] if 0 <= a < len(self._itens) else ""
        b = self._pos(ultimo)
        return tuple(self._itens[max(0, a):b + 1])

    def size(self):
        return len(self._itens)

    def curselection(self):
        return tuple(self._sel)

    def selection_includes(self, indice):
        return self._pos(indice) in self._sel

    def selection_set(self, primeiro, ultimo=None):
        a = self._pos(primeiro)
        b = a if ultimo is None else self._pos(ultimo)
        for i in range(max(0, a), min(b, len(self._itens) - 1) + 1):
            if i not in self._sel:
                self._sel.append(i)
        self._sel.sort()
        self._enviar()

    def selection_clear(self, primeiro, ultimo=None):
        a = self._pos(primeiro)
        b = a if ultimo is None else self._pos(ultimo)
        self._sel = [i for i in self._sel if not a <= i <= b]
        self._enviar()

    select_set = selection_set
    select_clear = selection_clear

    def see(self, indice):
        TK.listaVer(self._id, self._pos(indice))

    def activate(self, indice):
        pass

    def itemconfigure(self, indice, **opcoes):
        pass

    itemconfig = itemconfigure

    def yview(self, *args):
        return (0.0, 1.0)

    def xview(self, *args):
        return (0.0, 1.0)


class Scrollbar(Frame):
    def set(self, *args):
        pass


class Canvas(Widget):
    _tipo = "canvas"

    def _preparar(self):
        self._itens = {}
        self._ultimo = 0

    def _achatar(self, coords):
        plano = []
        for c in coords:
            if isinstance(c, (list, tuple)):
                plano.extend(self._achatar(c))
            else:
                plano.append(float(c))
        return plano

    def _criar(self, tipo, coords, opcoes):
        self._ultimo += 1
        n = self._ultimo
        tags = opcoes.get("tags", ())
        if isinstance(tags, str):
            tags = tags.split()
        plano = self._achatar(coords)
        self._itens[n] = {"tipo": tipo, "coords": plano, "tags": list(tags), "opcoes": dict(opcoes)}
        envio = {k: _serializar(v) for k, v in opcoes.items() if k != "tags"}
        TK.canvasCriar(self._id, n, tipo, json.dumps(plano), json.dumps(envio))
        return n

    def create_rectangle(self, *coords, **opcoes):
        return self._criar("rectangle", coords, opcoes)

    def create_oval(self, *coords, **opcoes):
        return self._criar("oval", coords, opcoes)

    def create_line(self, *coords, **opcoes):
        return self._criar("line", coords, opcoes)

    def create_polygon(self, *coords, **opcoes):
        return self._criar("polygon", coords, opcoes)

    def create_text(self, *coords, **opcoes):
        return self._criar("text", coords, opcoes)

    def create_image(self, *args, **kw):
        raise TclError("imagens no Canvas ainda não funcionam no PyCode")

    def _alvos(self, alvo):
        if alvo in (ALL,):
            return list(self._itens)
        if isinstance(alvo, int):
            return [alvo] if alvo in self._itens else []
        if isinstance(alvo, str) and alvo.isdigit():
            return [int(alvo)] if int(alvo) in self._itens else []
        return [n for n, item in self._itens.items() if alvo in item["tags"]]

    def delete(self, *alvos):
        for alvo in alvos:
            for n in self._alvos(alvo):
                del self._itens[n]
                TK.canvasDel(self._id, n)

    def coords(self, alvo, *novas):
        numeros = self._alvos(alvo)
        if not numeros:
            return []
        if not novas:
            return list(self._itens[numeros[0]]["coords"])
        plano = self._achatar(novas)
        for n in numeros:
            self._itens[n]["coords"] = plano
            TK.canvasCoords(self._id, n, json.dumps(plano))
        return None

    def move(self, alvo, dx, dy):
        for n in self._alvos(alvo):
            atuais = self._itens[n]["coords"]
            novas = [v + (float(dx) if i % 2 == 0 else float(dy)) for i, v in enumerate(atuais)]
            self._itens[n]["coords"] = novas
            TK.canvasCoords(self._id, n, json.dumps(novas))

    def itemconfigure(self, alvo, **opcoes):
        envio = {k: _serializar(v) for k, v in opcoes.items() if k != "tags"}
        for n in self._alvos(alvo):
            self._itens[n]["opcoes"].update(opcoes)
            TK.canvasConfig(self._id, n, json.dumps(envio))

    itemconfig = itemconfigure

    def itemcget(self, alvo, opcao):
        numeros = self._alvos(alvo)
        return self._itens[numeros[0]]["opcoes"].get(opcao, "") if numeros else ""

    def find_all(self):
        return tuple(self._itens)

    def find_withtag(self, tag):
        return tuple(self._alvos(tag))

    def gettags(self, alvo):
        numeros = self._alvos(alvo)
        return tuple(self._itens[numeros[0]]["tags"]) if numeros else ()

    def bbox(self, alvo):
        numeros = self._alvos(alvo)
        if not numeros:
            return None
        xs, ys = [], []
        for n in numeros:
            c = self._itens[n]["coords"]
            xs.extend(c[0::2])
            ys.extend(c[1::2])
        return (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))

    def tag_bind(self, alvo, sequencia=None, funcao=None, add=None):
        if funcao is None:
            return None
        cid = _registrar(funcao)
        for n in self._alvos(alvo):
            TK.canvasBind(self._id, n, str(sequencia), cid)
        return cid

    def tag_raise(self, alvo, *args):
        for n in self._alvos(alvo):
            TK.canvasOrdem(self._id, n, "topo")

    def tag_lower(self, alvo, *args):
        for n in self._alvos(alvo):
            TK.canvasOrdem(self._id, n, "fundo")

    lift = tag_raise
    lower = tag_lower


def _mensagem(tipo):
    def mostrar(title=None, message=None, **kw):
        TK.mensagem(str(title or ""), str(message or ""), tipo)
        return "ok"
    return mostrar


def _confirmar(title=None, message=None, **kw):
    return bool(TK.confirmar(str(title or ""), str(message or "")))


def _perguntar_texto(title=None, prompt=None, **kw):
    resposta = TK.perguntarTexto(str(title or ""), str(prompt or ""))
    dados = json.loads(str(resposta))
    return dados["valor"] if dados["ok"] else None


def _perguntar_numero(conversor):
    def perguntar(title=None, prompt=None, **kw):
        texto = _perguntar_texto(title, prompt)
        if texto is None:
            return None
        try:
            return conversor(texto)
        except ValueError:
            return None
    return perguntar


class _Estilo:
    def __init__(self, *args, **kw):
        pass

    def configure(self, *args, **kw):
        pass

    def map(self, *args, **kw):
        pass

    def theme_use(self, *args):
        return "default"

    def theme_names(self):
        return ("default",)


_Modulo = type(sys)

messagebox = _Modulo("tkinter.messagebox")
messagebox.showinfo = _mensagem("info")
messagebox.showwarning = _mensagem("aviso")
messagebox.showerror = _mensagem("erro")
messagebox.askyesno = _confirmar
messagebox.askokcancel = _confirmar
messagebox.askretrycancel = _confirmar
messagebox.askyesnocancel = _confirmar
messagebox.askquestion = lambda title=None, message=None, **kw: "yes" if _confirmar(title, message) else "no"

simpledialog = _Modulo("tkinter.simpledialog")
simpledialog.askstring = _perguntar_texto
simpledialog.askinteger = _perguntar_numero(int)
simpledialog.askfloat = _perguntar_numero(float)

ttk = _Modulo("tkinter.ttk")
ttk.Frame = Frame
ttk.LabelFrame = LabelFrame
ttk.Label = Label
ttk.Button = Button
ttk.Entry = Entry
ttk.Style = _Estilo

for _nome, _modulo in (("messagebox", messagebox), ("simpledialog", simpledialog), ("ttk", ttk)):
    sys.modules["tkinter." + _nome] = _modulo

__all__ = [
    "Tk", "Toplevel", "mainloop", "Frame", "LabelFrame", "Label", "Message", "Button", "Entry", "Text", "Canvas", "Listbox", "Scrollbar",
    "StringVar", "IntVar", "DoubleVar", "BooleanVar", "Variable", "Event", "TclError",
    "END", "INSERT", "LEFT", "RIGHT", "TOP", "BOTTOM", "X", "Y", "BOTH", "NONE",
    "N", "S", "E", "W", "NW", "NE", "SW", "SE", "CENTER", "NS", "EW", "NSEW",
    "NORMAL", "DISABLED", "ACTIVE", "HIDDEN", "RAISED", "SUNKEN", "FLAT", "RIDGE", "GROOVE", "SOLID",
    "HORIZONTAL", "VERTICAL", "WORD", "CHAR", "YES", "NO", "TRUE", "FALSE", "ALL",
]
