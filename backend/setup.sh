#!/usr/bin/env bash
# Cria (ou repara) o ambiente virtual do backend e instala TODAS as dependências.
# Uso, a partir da raiz do projeto:  bash backend/setup.sh
# Pode ser executado quantas vezes for preciso: um .venv incompleto é recriado automaticamente.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$BACKEND_DIR/.venv"
VENV_PYTHON="$VENV/bin/python"

# 1) Localiza um Python 3.11+
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3.11 ou superior não encontrado." >&2
  exit 1
fi

# 2) Cria o venv; se já existir mas estiver incompleto (sem pip), recria do zero
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  criado=0
  for tentativa in 1 2 3; do
    if [ -d "$VENV" ]; then
      echo "Removendo ambiente virtual incompleto (tentativa $tentativa)..."
      rm -rf "$VENV"
    fi
    echo "Criando ambiente virtual (tentativa $tentativa)..."
    if "$PYTHON" -m venv "$VENV" && "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
      criado=1
      break
    fi
    sleep 3
  done
  if [ "$criado" -ne 1 ]; then
    echo "Não foi possível criar o ambiente virtual em '$VENV'." >&2
    exit 1
  fi
fi

# 3) Instala as dependências (é aqui que os pacotes realmente são instalados)
echo "Instalando dependências..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt"

# 4) Verifica: dependências consistentes e aplicação importável
"$VENV_PYTHON" -m pip check
(cd "$BACKEND_DIR" && "$VENV_PYTHON" -c \
  "import app.main, cryptography, multipart, pymongo, pytest, httpx; print('Aplicação importada com sucesso.')")

echo
echo "Backend pronto. Para iniciar:"
echo "  cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000"
