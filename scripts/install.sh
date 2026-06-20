#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEMORY_HOME="${MNEME_HOME:-${HERMES_HOME:-$HOME/.hermes}}"
export HERMES_HOME="$MEMORY_HOME"
INSTALL_HERMES=1
PYTHON_BIN="${PYTHON_BIN:-}"

usage() {
  cat <<'EOF'
Mneme Memory MCP installer

Usage:
  ./scripts/install.sh [--no-hermes-install]

By default this installs Mneme into .venv and installs Hermes Agent if the
`hermes` command is not already available.

Environment:
  MNEME_HOME    Memory home to use. Defaults to HERMES_HOME or ~/.hermes.
  HERMES_HOME   Hermes-compatible memory home.
  PYTHON_BIN    Python 3.10+ binary to use. Auto-detected when unset.
EOF
}

find_python() {
  if [ -n "$PYTHON_BIN" ]; then
    printf '%s\n' "$PYTHON_BIN"
    return 0
  fi

  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
      then
        command -v "$candidate"
        return 0
      fi
    fi
  done

  return 1
}

for arg in "$@"; do
  case "$arg" in
    --no-hermes|--no-hermes-install)
      INSTALL_HERMES=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

find_hermes() {
  if command -v hermes >/dev/null 2>&1; then
    command -v hermes
    return 0
  fi

  for candidate in "$HOME/.local/bin/hermes" "$HOME/.hermes/bin/hermes" "$HOME/.hermes/hermes-agent/hermes"; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

echo "==> Mneme Memory MCP"
echo "repo: $ROOT"
echo "memory home: $MEMORY_HOME"

if ! PYTHON_BIN="$(find_python)"; then
  echo "Python 3.10 or newer is required." >&2
  echo "Install Python 3.10+ or set PYTHON_BIN=/path/to/python3.10." >&2
  exit 1
fi

echo "python: $PYTHON_BIN"

if ! HERMES_BIN="$(find_hermes)"; then
  if [ "$INSTALL_HERMES" -eq 1 ]; then
    echo "==> Hermes Agent not found. Installing Hermes Agent..."
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
  else
    echo "==> Hermes Agent not found. Skipping Hermes install by request."
  fi
else
  echo "==> Hermes Agent found: $HERMES_BIN"
fi

"$PYTHON_BIN" -m venv --clear "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -e "$ROOT"

mkdir -p "$MEMORY_HOME/memories"
[ -f "$MEMORY_HOME/memories/USER.md" ] || printf '# USER.md\n\n' > "$MEMORY_HOME/memories/USER.md"
[ -f "$MEMORY_HOME/memories/MEMORY.md" ] || printf '# MEMORY.md\n\n' > "$MEMORY_HOME/memories/MEMORY.md"

echo
"$ROOT/.venv/bin/mneme-memory-doctor"

cat <<EOF

==> Add Mneme to your MCP client

Codex ~/.codex/config.toml:

[mcp_servers.mneme_memory]
command = "$ROOT/.venv/bin/mneme-memory-mcp"
args = []
startup_timeout_sec = 120

[mcp_servers.mneme_memory.env]
HERMES_HOME = "$HERMES_HOME"

Claude Code ~/.claude.json:

{
  "mcpServers": {
    "mneme-memory": {
      "type": "stdio",
      "command": "$ROOT/.venv/bin/mneme-memory-mcp",
      "args": [],
      "env": {
        "HERMES_HOME": "$HERMES_HOME"
      }
    }
  }
}

Restart your MCP client after adding the config.
EOF
