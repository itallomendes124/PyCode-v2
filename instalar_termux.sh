#!/data/data/com.termux/files/usr/bin/bash
set -e
ORIGEM="$(cd "$(dirname "$0")" && pwd)"
DESTINO="$HOME/PyCode-app"

echo "== Instalando o PyCode no Termux =="
if ! command -v python > /dev/null 2>&1; then
  pkg install -y python
fi
if [ ! -d "$HOME/storage/shared" ]; then
  echo "Toque em PERMITIR na janela de acesso aos arquivos."
  termux-setup-storage || true
  sleep 4
fi
if [ "$ORIGEM" != "$DESTINO" ]; then
  rm -rf "$DESTINO"
  cp -r "$ORIGEM" "$DESTINO"
fi
chmod +x "$DESTINO/termux/PyCode" "$DESTINO/termux/diagnostico.sh"
PASTA="$HOME/storage/shared/PyCode"
[ -d "$HOME/storage/shared" ] || PASTA="$HOME/PyCode"
mkdir -p "$PASTA" "$HOME/.shortcuts/icons"
rm -f "$HOME/.shortcuts/tasks/PyCode"
cp "$DESTINO/termux/PyCode" "$HOME/.shortcuts/PyCode"
chmod +x "$HOME/.shortcuts/PyCode"
cp "$DESTINO/web/icone-192.png" "$HOME/.shortcuts/icons/PyCode.png"

echo "Baixando o editor (só desta vez, precisa de internet)..."
if python "$DESTINO/pycode_servidor.py" --pasta "$PASTA" --baixar; then
  echo "Editor baixado."
else
  echo "Falhou o download. Conecte à internet e rode este instalador de novo."
  exit 1
fi

echo
echo "Pronto! Seus projetos ficam em: Armazenamento interno/PyCode"
echo
echo "Ícone na tela inicial (se já tinha um antigo, remova e crie de novo):"
echo "  1. Segure o dedo na tela inicial > Widgets > Termux:Widget."
echo "  2. Escolha 'Termux shortcut' e selecione PyCode."
echo
echo "Abrir agora sem o ícone:  bash ~/.shortcuts/PyCode"
echo "Se algo falhar:           bash ~/PyCode-app/termux/diagnostico.sh"
