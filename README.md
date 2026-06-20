# Caduceus Memory MCP

A local shared-memory MCP server for Claude, Codex, Hermes, and other MCP-aware agents.

The goal is simple: one durable memory layer that every agent can read from and write to.

```text
Claude Code  ----\
Codex         ----- caduceus-memory-mcp ---- ~/.hermes
Hermes        ----/                         memories/ + memory_store.db
```

## Why Caduceus?

Hermes carries messages. The caduceus is Hermes' staff. This project is the staff: the bridge that lets different agents carry the same memory forward.

## What It Stores

Caduceus stores memory in two local forms:

- Markdown files for always-on human-readable memory:
  - `~/.hermes/memories/USER.md`
  - `~/.hermes/memories/MEMORY.md`
- SQLite FTS fact store for searchable recall:
  - `~/.hermes/memory_store.db`

It is designed to sit next to Hermes, but it does not require Hermes Agent to be running.

## Tools

The MCP server exposes:

- `memory_summary` - read the current Markdown memory summary
- `memory_search` - search the SQLite fact store
- `memory_list` - list recent facts
- `memory_add` - add a durable memory
- `memory_update` - update a fact by id
- `memory_remove` - remove a fact by id

## Install From A Clone

```bash
git clone https://github.com/ethos-zero/caduceus-memory-mcp.git
cd caduceus-memory-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

Your server command will be:

```bash
/absolute/path/to/caduceus-memory-mcp/.venv/bin/caduceus-memory-mcp
```

## Configure Codex

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.caduceus_memory]
command = "/absolute/path/to/caduceus-memory-mcp/.venv/bin/caduceus-memory-mcp"
args = []
startup_timeout_sec = 120

[mcp_servers.caduceus_memory.env]
HERMES_HOME = "/Users/YOU/.hermes"
```

Restart Codex or open a fresh session so it reloads MCP servers.

## Configure Claude Code

Add this to `~/.claude.json`:

```json
{
  "mcpServers": {
    "caduceus-memory": {
      "type": "stdio",
      "command": "/absolute/path/to/caduceus-memory-mcp/.venv/bin/caduceus-memory-mcp",
      "args": [],
      "env": {
        "HERMES_HOME": "/Users/YOU/.hermes"
      }
    }
  }
}
```

If you already have other `mcpServers`, merge the `caduceus-memory` entry into the existing object.

## Optional Claude SessionStart Hook

Claude Code can also auto-inject the Markdown memory at the beginning of each session. Copy:

```bash
examples/sessionstart-hermes-memory.sh
```

to something like:

```bash
~/.claude/hooks/sessionstart-hermes-memory.sh
```

Then add a `SessionStart` hook in `~/.claude/settings.json`.

The MCP server is still the source of truth for search and writes; the hook just makes the high-signal Markdown summary visible immediately.

## Environment Variables

Defaults are chosen for Hermes compatibility:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CADUCEUS_HOME` | unset | Primary Caduceus home override |
| `HERMES_HOME` | `~/.hermes` | Hermes-compatible memory home |
| `CADUCEUS_MEMORY_DIR` | `$HOME/memories` under resolved home | Markdown memory directory |
| `CADUCEUS_DB_PATH` | `$HOME/memory_store.db` under resolved home | SQLite fact store path |

Priority for home is:

1. `CADUCEUS_HOME`
2. `HERMES_HOME`
3. `~/.hermes`

## Local Smoke Test

```bash
python -m unittest discover -s tests -v
```

To test through an MCP client, use any MCP-compatible inspector/client and run:

```bash
caduceus-memory-mcp
```

## Privacy

This server is local-first. It does not send memory anywhere by itself. Any agent you connect to it can read or write the configured local memory, so only connect agents you trust.

## Name Ideas

If you want a different name before publishing:

- `caduceus-memory-mcp` - Hermes' staff; strong bridge metaphor
- `mneme-mcp` - Greek memory spirit; short and direct
- `mnemosyne-mcp` - Greek goddess of memory; beautiful but harder to type
- `iris-memory-mcp` - divine messenger bridge; lighter than Hermes
- `atlas-memory-mcp` - carries the world of context
- `aegis-memory-mcp` - protective shared memory layer
- `threadkeeper-mcp` - less mythic, very clear
