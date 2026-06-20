# Mneme Memory MCP

The memory that grows with every agent.

![Mneme Memory MCP hero artwork](assets/mneme-hero.png)

Mneme is a local-first shared memory layer for Claude, Codex, Hermes, and any MCP-aware agent you trust.

It gives your agents one durable mind: preferences, project state, tool setup, decisions, and long-running context that survive new chats and new clients.

```text
Claude Code  -----\
Codex          ----- mneme-memory-mcp ----- ~/.hermes
Hermes Agent  -----/                          memories/ + memory_store.db
```

## What It Does

- Remembers across chats, agents, and clients
- Shares one Hermes-compatible memory home
- Stores human-readable memory in Markdown
- Stores searchable facts in SQLite FTS
- Exposes memory through MCP tools
- Installs beside Hermes Agent, and can bootstrap Hermes when it is missing

## Why Mneme?

Mneme means memory. Hermes carries messages; Mneme keeps them from disappearing. This project is the bridge that lets every connected agent return to the same remembered context.

## Artwork

The project artwork uses an original ultramarine-and-ivory engraving style: two agent forms, a shared ribbon between them, and a persistent memory layer above. It is meant to nod toward the mythic Hermes lineage without copying or implying affiliation with Hermes Agent, Nous Research, or any other project.

Additional documentation artwork lives in [docs/artwork.md](docs/artwork.md).

## Quick Install

```bash
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
./scripts/install.sh
```

The installer:

- checks for `hermes`
- installs Hermes Agent with the official Hermes installer if missing
- creates a local `.venv`
- installs `mneme-memory-mcp`
- creates `~/.hermes/memories`
- prints ready-to-paste Codex and Claude MCP config

To skip Hermes installation:

```bash
./scripts/install.sh --no-hermes-install
```

Check the setup:

```bash
.venv/bin/mneme-memory-doctor
```

## Hermes Pairing

Mneme is designed to sit next to [Hermes Agent](https://github.com/NousResearch/hermes-agent), the agent that grows with you. Hermes provides the agent runtime and desktop experience; Mneme provides a small shared-memory MCP bridge that other agents can use directly.

For the full setup, install both:

- Hermes Agent for the local agent environment
- Mneme Memory MCP for shared memory across Codex, Claude Code, Hermes, and other MCP clients

More details live in [docs/hermes.md](docs/hermes.md).

## Memory Store

Mneme stores memory in two local forms:

- Markdown files for always-on human-readable memory:
  - `~/.hermes/memories/USER.md`
  - `~/.hermes/memories/MEMORY.md`
- SQLite FTS fact store for searchable recall:
  - `~/.hermes/memory_store.db`

It is designed to sit next to Hermes, but the MCP memory server does not require Hermes Agent to be running.

## Tools

The MCP server exposes:

- `memory_summary` - read the current Markdown memory summary
- `memory_search` - search the SQLite fact store
- `memory_list` - list recent facts
- `memory_add` - add a durable memory
- `memory_update` - update a fact by id
- `memory_remove` - remove a fact by id

## Manual Install

```bash
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

Your server command will be:

```bash
/absolute/path/to/mneme-memory-mcp/.venv/bin/mneme-memory-mcp
```

## Configure Codex

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.mneme_memory]
command = "/absolute/path/to/mneme-memory-mcp/.venv/bin/mneme-memory-mcp"
args = []
startup_timeout_sec = 120

[mcp_servers.mneme_memory.env]
HERMES_HOME = "/Users/YOU/.hermes"
```

Restart Codex or open a fresh session so it reloads MCP servers.

To also expose Hermes Agent itself to Codex, add a Hermes MCP server using the `hermes` command installed by Hermes Agent:

```toml
[mcp_servers.hermes]
command = "hermes"
args = ["mcp", "serve", "--accept-hooks"]
startup_timeout_sec = 120
```

## Configure Claude Code

Add this to `~/.claude.json`:

```json
{
  "mcpServers": {
    "mneme-memory": {
      "type": "stdio",
      "command": "/absolute/path/to/mneme-memory-mcp/.venv/bin/mneme-memory-mcp",
      "args": [],
      "env": {
        "HERMES_HOME": "/Users/YOU/.hermes"
      }
    }
  }
}
```

If you already have other `mcpServers`, merge the `mneme-memory` entry into the existing object.

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
| `MNEME_HOME` | unset | Primary Mneme home override |
| `HERMES_HOME` | `~/.hermes` | Hermes-compatible memory home |
| `MNEME_MEMORY_DIR` | `$HOME/memories` under resolved home | Markdown memory directory |
| `MNEME_DB_PATH` | `$HOME/memory_store.db` under resolved home | SQLite fact store path |

Priority for home is:

1. `MNEME_HOME`
2. `HERMES_HOME`
3. `~/.hermes`

## Local Smoke Test

```bash
python -m unittest discover -s tests -v
```

To test through an MCP client, use any MCP-compatible inspector/client and run:

```bash
mneme-memory-mcp
```

## Privacy

This server is local-first. It does not send memory anywhere by itself. Any agent you connect to it can read or write the configured local memory, so only connect agents you trust.
