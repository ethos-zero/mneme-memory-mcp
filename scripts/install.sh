#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEMORY_HOME="${MNEME_HOME:-${HERMES_HOME:-$HOME/.hermes}}"
export HERMES_HOME="$MEMORY_HOME"
INSTALL_HERMES=1
CONFIGURE_CLIENTS=1
INSTALL_AGENT_PLUGINS=1
PYTHON_BIN="${PYTHON_BIN:-}"

usage() {
  cat <<'EOF'
Mneme Memory MCP installer

Usage:
  ./scripts/install.sh [--no-hermes-install] [--no-client-config] [--no-agent-plugins]

By default this installs Mneme into .venv and installs Hermes Agent if the
`hermes` command is not already available. It also tries to wire Mneme into
Codex and Claude Code, install OpenAI's Claude-to-Codex plugin, and install
Ponytail for both clients when their CLIs are present.

Options:
  --no-hermes-install  Skip automatic Hermes Agent installation.
  --no-client-config   Do not modify Codex or Claude MCP configuration.
  --no-agent-plugins   Do not install Codex/Claude/Ponytail plugins.
  --memory-only        Same as --no-client-config --no-agent-plugins.

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
    --no-client-config)
      CONFIGURE_CLIENTS=0
      ;;
    --no-agent-plugins)
      INSTALL_AGENT_PLUGINS=0
      ;;
    --memory-only)
      CONFIGURE_CLIENTS=0
      INSTALL_AGENT_PLUGINS=0
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

run_optional() {
  local label="$1"
  shift
  echo "==> $label"
  if "$@"; then
    return 0
  fi
  local code=$?
  echo "warning: $label failed with exit $code; continuing." >&2
  return 0
}

configure_clients() {
  if [ "$CONFIGURE_CLIENTS" -ne 1 ]; then
    echo "==> Skipping Codex/Claude MCP configuration."
    return 0
  fi

  if command -v codex >/dev/null 2>&1; then
    codex mcp remove mneme_memory >/dev/null 2>&1 || true
    run_optional \
      "Configuring Codex MCP server: mneme_memory" \
      codex mcp add --env "HERMES_HOME=$HERMES_HOME" mneme_memory -- "$ROOT/.venv/bin/mneme-memory-mcp"
  else
    echo "==> Codex CLI not found; skipping Codex MCP configuration."
  fi

  if command -v claude >/dev/null 2>&1; then
    claude mcp remove mneme-memory >/dev/null 2>&1 || true
    run_optional \
      "Configuring Claude Code MCP server: mneme-memory" \
      claude mcp add -s user mneme-memory -e "HERMES_HOME=$HERMES_HOME" -- "$ROOT/.venv/bin/mneme-memory-mcp"
  else
    echo "==> Claude CLI not found; skipping Claude MCP configuration."
  fi
}

install_agent_plugins() {
  if [ "$INSTALL_AGENT_PLUGINS" -ne 1 ]; then
    echo "==> Skipping agent plugin installation."
    return 0
  fi

  if command -v claude >/dev/null 2>&1; then
    run_optional \
      "Adding Claude Code marketplace: openai/codex-plugin-cc" \
      claude plugin marketplace add openai/codex-plugin-cc
    run_optional \
      "Installing Claude Code plugin: codex@openai-codex" \
      claude plugin install -s user codex@openai-codex
    run_optional \
      "Adding Claude Code marketplace: DietrichGebert/ponytail" \
      claude plugin marketplace add DietrichGebert/ponytail
    run_optional \
      "Installing Claude Code plugin: ponytail@ponytail" \
      claude plugin install -s user ponytail@ponytail
  else
    echo "==> Claude CLI not found; skipping Claude plugin installation."
  fi

  if command -v codex >/dev/null 2>&1; then
    run_optional \
      "Adding Codex marketplace: DietrichGebert/ponytail" \
      codex plugin marketplace add DietrichGebert/ponytail
    run_optional \
      "Installing Codex plugin: ponytail@ponytail" \
      codex plugin add ponytail@ponytail
  else
    echo "==> Codex CLI not found; skipping Codex plugin installation."
  fi
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
echo
configure_clients
echo
install_agent_plugins

cat <<EOF

==> Mneme agent mesh

The installer attempted to configure:

- Mneme MCP in Codex and Claude Code
- OpenAI codex-plugin-cc in Claude Code for Claude -> Codex delegation
- Ponytail in Codex and Claude Code for smaller, safer code generation

If automatic client configuration was skipped or failed, add Mneme manually.

Codex:

[mcp_servers.mneme_memory]
command = "$ROOT/.venv/bin/mneme-memory-mcp"
args = []
startup_timeout_sec = 120

[mcp_servers.mneme_memory.env]
HERMES_HOME = "$HERMES_HOME"

Claude Code:

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

Restart Codex and Claude Code after install so MCP servers and plugins reload.
EOF
