#!/usr/bin/env bash
# Wrapper para ejecutar el cotizador.
# Activa el virtualenv y ejecuta el módulo.
# Uso: ./run.sh 37000  o  ./run.sh --cp 37000

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Activar virtualenv
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
else
    echo "❌ No se encontró el virtualenv en .venv/"
    echo "   Créalo con: python3 -m venv .venv && source .venv/bin/activate && pip install requests"
    exit 1
fi

exec python -m src "$@"
