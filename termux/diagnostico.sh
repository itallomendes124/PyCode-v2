#!/data/data/com.termux/files/usr/bin/bash
APP="$HOME/PyCode-app"
PASTA="$HOME/storage/shared/PyCode"
[ -d "$HOME/storage/shared" ] || PASTA="$HOME/PyCode"
item() { if eval "$2"; then echo "  ok     $1"; else echo "  FALTA  $1"; fi; }
echo "== Diagnóstico do PyCode =="
echo "  Termux: ${TERMUX_VERSION:-?} (${TERMUX_APK_RELEASE:-?})"
echo "  Python: $(python --version 2>&1)"
item "app em $APP" '[ -f "$APP/pycode_servidor.py" ]'
item "tkinter do PyCode (ponte)" '[ -f "$APP/ponte/tkinter/__init__.py" ]'
item "editor baixado" '[ -f "$PASTA/.libs/ace/ace.js" ]'
item "atalho ~/.shortcuts/PyCode" '[ -x "$HOME/.shortcuts/PyCode" ]'
item "acesso ao armazenamento" '[ -d "$HOME/storage/shared" ]'
item "termux-open-url" 'command -v termux-open-url > /dev/null'
item "servidor ligado agora" 'python -c "import urllib.request as u; u.urlopen(u.Request(\"http://127.0.0.1:8765/api/vivo\", headers={\"X-PyCode\": \"1\"}), timeout=1)" 2> /dev/null'
echo
echo "== Últimas linhas do log ($PASTA/termux.log) =="
tail -n 15 "$PASTA/termux.log" 2> /dev/null || echo "  (sem log ainda)"
