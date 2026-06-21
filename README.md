# Mneme Memory MCP

The memory that grows with every agent.

![Mneme Memory MCP hero artwork](assets/mneme-hero.png)

Mneme is a local-first shared memory and agent-mesh layer for Claude, Codex, Hermes, and any MCP-aware agent you trust.

It gives your agents one durable mind and one shared bridge: preferences, project state, tool setup, decisions, long-running context, and peer-agent delegation that survive new chats and new clients.

```text
Claude Code  <---->  mneme-memory-mcp  <---->  Codex
       \                 |   |                  /
        \                |   |                 /
         \-------->  ~/.hermes memory  <------/
                         |
                    Hermes Agent
```

## What It Does

- Remembers across chats, agents, and clients
- Installs always-on memory instructions for fresh Claude and Codex chats
- Auto-injects Markdown memory into new Claude Code sessions
- Shares one Hermes-compatible memory home
- Stores human-readable memory in Markdown
- Stores searchable facts in SQLite FTS
- Exposes memory through MCP tools
- Installs beside Hermes Agent, and can bootstrap Hermes when it is missing
- Wires Claude and Codex together through MCP and the OpenAI Claude-to-Codex plugin
- Installs Ponytail for smaller, safer code-generation behavior in both clients

## Why Mneme?

Mneme means memory. Hermes carries messages; Mneme keeps them from disappearing. This project is the bridge that lets every connected agent return to the same remembered context.

## Artwork

The project artwork uses an original ultramarine-and-ivory engraving style: two agent forms, a shared ribbon between them, and a persistent memory layer above. It is meant to nod toward the mythic Hermes lineage without copying or implying affiliation with Hermes Agent, Nous Research, or any other project.

## Platform support

The Mneme package (MCP server, memory tools, and CLIs) is pure Python and runs on macOS, Linux, and Windows.

- **macOS / Linux:** use the one-command installer below (`./scripts/install.sh` is bash).
- **Windows:** bash is not native, so use the [Manual Install](#manual-install) plus [Configure Codex](#configure-codex) and [Configure Claude Code](#configure-claude-code) steps (all cross-platform), or run the installer under WSL or Git Bash.

Hermes auto-install and the Claude `SessionStart` memory hook are macOS/Linux only. On Windows, continuity still works through the managed `AGENTS.md`/`CLAUDE.md` instructions and the Mneme MCP tools.

## Quick Install

```bash
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
./scripts/install.sh
```

When run in an interactive terminal, the installer asks which memory profile you want:

| Profile | Best For | Memory Home | Global Claude/Codex Instructions |
| --- | --- | --- | --- |
| `global` | A personal machine where every fresh Claude/Codex chat should share memory | `~/.hermes` by default | Yes |
| `project` | A cloned repo, shared setup, or isolated workspace | `.env` value, defaulting to `./.mneme` | No |
| `server` | Manual wiring or cautious evaluation | Your existing env/defaults | No |

Non-interactive installs keep the previous default and use `global`.

The installer:

- checks for `hermes`
- installs Hermes Agent with the official Hermes installer if missing
- creates a local `.venv`
- installs `mneme-memory-mcp`
- creates `~/.hermes/memories`
- installs always-on Mneme instructions into global Claude and Codex guidance files
- configures a Claude Code `SessionStart` hook that injects the shared Markdown memory into fresh sessions
- configures Mneme as an MCP server in Codex and Claude Code when those CLIs are present
- installs [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) into Claude Code for Claude -> Codex delegation
- installs [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) into Codex and Claude Code for minimal, safer implementation behavior
- prints manual fallback config

Choose a profile directly:

```bash
./scripts/install.sh --profile global
./scripts/install.sh --profile project
./scripts/install.sh --profile server
```

To skip Hermes installation:

```bash
./scripts/install.sh --no-hermes-install
```

For memory-only setup without client/plugin changes:

```bash
./scripts/install.sh --memory-only
```

To keep MCP/plugin setup but skip global memory instructions:

```bash
./scripts/install.sh --no-continuity
```

For a project/env-scoped setup using a specific env file:

```bash
./scripts/install.sh --profile project --env-file /path/to/.env
```

You can start from `.env.example`.

If that file has no `MNEME_HOME` or `HERMES_HOME`, Mneme adds:

```env
MNEME_HOME=/absolute/path/to/mneme-memory-mcp/.mneme
```

Check the setup:

```bash
.venv/bin/mneme-memory-doctor
```

## Agent Mesh

![Mneme agent bridge artwork](assets/docs/agent-bridge.png)

Mneme makes Claude and Codex meet in the same memory field.

- Claude -> Codex: installed through OpenAI's `codex-plugin-cc` Claude Code plugin.
- Codex -> Claude: exposed through Mneme's `delegate_to_claude` MCP tool.
- Shared memory: both clients use the same Mneme MCP server pointed at the same Hermes-compatible memory home.
- Always-on continuity: global Claude/Codex instructions and a Claude `SessionStart` hook make new chats consult shared memory before substantive work.
- Efficient implementation mode: Ponytail is installed for both clients when available.

More details live in [docs/agent-mesh.md](docs/agent-mesh.md), [docs/always-on-memory.md](docs/always-on-memory.md), and [docs/ponytail.md](docs/ponytail.md).

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
- `agent_bridge_status` - check local Claude, Codex, and Node readiness
- `delegate_to_claude` - ask Claude Code to handle a one-shot task with Mneme memory injected
- `delegate_to_codex` - ask Codex to handle a one-shot task with Mneme memory injected

Mneme also installs these local CLI commands:

- `mneme-memory` - read, search, list, and add shared memory without an MCP client
- `mneme-memory-continuity` - install or inspect always-on Claude/Codex memory continuity
- `mneme-memory-env-mcp` - run the MCP server after loading memory settings from a `.env` file

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

## Always-On Client Memory

Always-on client memory is the `global` profile. It is ideal for one trusted personal machine, because every configured local Claude and Codex session is instructed to start from the same memory layer.

The installer writes managed instruction blocks to:

- `~/.codex/AGENTS.md`
- `~/.claude/CLAUDE.md`

It also installs this Claude Code hook:

```text
~/.claude/hooks/mneme-memory-sessionstart.sh
```

and merges it into `~/.claude/settings.json` under `SessionStart`.

The MCP server is still the source of truth for search and writes; the global instructions and hook make the high-signal memory summary visible immediately in fresh chats.

Read the full behavior in [docs/always-on-memory.md](docs/always-on-memory.md).

For repo-scoped memory, use `--profile project`. That profile configures MCP clients through `mneme-memory-env-mcp`, which reads `MNEME_HOME` or `HERMES_HOME` from `.env`, and it does not install global Claude/Codex memory instructions.

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

The `delegate_to_claude` and `delegate_to_codex` tools run the other CLI on your machine non-interactively. `delegate_to_codex` uses Codex's `workspace-write` sandbox with approvals disabled (and can be set to `danger-full-access`), so it can change files in the working directory on its own. Treat them like any autonomous agent and enable them only for directories and tasks you trust.
