# Mneme Memory MCP

The memory that grows with every agent.

![Mneme Memory MCP](assets/mneme-hero.png)

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
- Automatically indexes local Claude and Codex conversation snippets into searchable memory
- Shares one Hermes-compatible memory home
- Stores human-readable memory in Markdown
- Stores searchable facts in SQLite FTS
- Exposes memory through MCP tools
- Installs beside Hermes Agent, and can bootstrap Hermes when it is missing
- Wires Claude and Codex together through MCP and the OpenAI Claude-to-Codex plugin
- Installs Ponytail for smaller, safer code-generation behavior in both clients

## Why Mneme?

Mneme means memory. Hermes carries messages; Mneme keeps them from disappearing. This project is the bridge that lets every connected agent return to the same remembered context.

## Platform support

The Mneme package (MCP server, memory tools, and CLIs) is pure Python and runs on macOS, Linux, and Windows.

- **macOS / Linux:** use the one-command installer below (`./scripts/install.sh` is bash).
- **Windows:** use the native PowerShell installer below (`.\scripts\install.ps1`).

Hermes auto-install uses the official bash installer on macOS/Linux. On Windows, Mneme looks for an existing Hermes Agent install and continues with Mneme MCP memory when Hermes is not present.

## Quick Install

macOS / Linux:

```bash
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
./scripts/install.sh
```

Windows PowerShell:

```powershell
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

Both installers support these memory profiles:

| Profile | Best For | Memory Home | Global Claude/Codex Instructions |
| --- | --- | --- | --- |
| `global` | A personal machine where every fresh Claude/Codex chat should share memory | `~/.hermes` by default | Yes |
| `project` | A cloned repo, shared setup, or isolated workspace | `.env` value, defaulting under the platform Mneme data directory | No |
| `server` | Manual wiring or cautious evaluation | Your existing env/defaults | No |

Both installers ask which profile you want when run interactively. Non-interactive installs, including installs run by an AI agent or automation, stop until the user chooses `global`, `project`, or `server`. After the user answers, rerun with both `--profile`/`-Profile` and `--profile-confirmed`/`-ProfileConfirmed`, or set `MNEME_SETUP_PROFILE` plus `MNEME_PROFILE_CONFIRMED=1`.

The installer:

- checks for `hermes`
- installs Hermes Agent with the official Hermes installer if missing on macOS/Linux
- creates a managed Python venv under the platform data directory
- installs `mneme-memory-mcp` into that managed venv
- creates the configured memory home and `memories` directory
- for the `global` profile, installs always-on Mneme instructions into global Claude and Codex guidance files
- for the `global` profile, configures a Claude Code `SessionStart` hook that injects the shared Markdown memory into fresh sessions
- for the `global` profile, configures a Claude Code `UserPromptSubmit` hook that adds shared memory context before every future prompt
- for the `global` profile, configures Claude and Codex capture hooks that index recent local conversation snippets into Mneme search
- configures Mneme as an MCP server in Codex and Claude Code when those CLIs are present, and writes Claude user-scope MCP config directly when the Claude CLI is unavailable
- installs [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) into Claude Code for Claude -> Codex delegation
- installs [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) into Codex and Claude Code for minimal, safer implementation behavior
- prints manual fallback config

Ponytail is part of the default client-wiring path for `global` and `project` profiles when the relevant CLIs are available and runnable. It is skipped only for `server`, `--no-agent-plugins`/`-NoAgentPlugins`, or `--memory-only`/`-MemoryOnly`.

Preselect a profile after the user has chosen it:

```bash
./scripts/install.sh --profile global --profile-confirmed
./scripts/install.sh --profile project --profile-confirmed
./scripts/install.sh --profile server --profile-confirmed
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile project -ProfileConfirmed
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile server -ProfileConfirmed
```

If a profile is supplied without the confirmation flag, an interactive shell asks you to type the profile name before it proceeds; a non-interactive shell exits so an agent can ask the user first.

To skip Hermes installation:

```bash
./scripts/install.sh --profile global --profile-confirmed --no-hermes-install
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed -NoHermesInstall
```

For memory-only setup without client/plugin changes:

```bash
./scripts/install.sh --profile global --profile-confirmed --memory-only
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed -MemoryOnly
```

To keep MCP/plugin setup but skip global memory instructions:

```bash
./scripts/install.sh --profile global --profile-confirmed --no-continuity
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed -NoContinuity
```

For a project/env-scoped setup using a specific env file:

```bash
./scripts/install.sh --profile project --profile-confirmed --env-file /path/to/.env
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile project -ProfileConfirmed -EnvFile C:\path\to\.env
```

You can start from `.env.example`.

If that file has no `MNEME_HOME` or `HERMES_HOME`, Mneme adds:

```env
MNEME_HOME=/Users/YOU/.local/share/mneme-memory-mcp/projects/mneme-memory-mcp
```

Check the setup:

```bash
~/.local/share/mneme-memory-mcp/venv/bin/mneme-memory-doctor
```

Windows:

```powershell
& "$env:LOCALAPPDATA\mneme-memory-mcp\venv\Scripts\python.exe" -m mneme_memory_mcp.doctor
```

## Install Paths

The installer does not create runtime folders on your Desktop. If you clone the repo on your Desktop, the visible Desktop item is just the cloned repo folder.

Default installer paths:

| Item | macOS / Linux | Windows |
| --- | --- | --- |
| Managed install directory | `~/.local/share/mneme-memory-mcp` | `%LOCALAPPDATA%\mneme-memory-mcp` |
| Python virtualenv | `~/.local/share/mneme-memory-mcp/venv` | `%LOCALAPPDATA%\mneme-memory-mcp\venv` |
| Global memory profile | `~/.hermes` | `%USERPROFILE%\.hermes` unless `MNEME_HOME`/`HERMES_HOME` is set |
| Project memory profile | `~/.local/share/mneme-memory-mcp/projects/<repo-name>` | `%LOCALAPPDATA%\mneme-memory-mcp\projects\<repo-name>` |
| Project env file | `<repo>/.env` unless `--env-file` is passed | `<repo>\.env` unless `-EnvFile` is passed |
| Codex global instructions | `~/.codex/AGENTS.md` | `%USERPROFILE%\.codex\AGENTS.md` |
| Codex capture notify wrapper | `~/.codex/mneme-memory-notify.sh` | `%USERPROFILE%\.codex\mneme-memory-notify.cmd` |
| Claude global instructions | `~/.claude/CLAUDE.md` | `%USERPROFILE%\.claude\CLAUDE.md` |
| Claude memory hook | `~/.claude/hooks/mneme-memory-sessionstart.sh` | `%USERPROFILE%\.claude\hooks\mneme-memory-sessionstart.cmd` |
| Claude capture hook | `~/.claude/hooks/mneme-memory-capture.sh` | `%USERPROFILE%\.claude\hooks\mneme-memory-capture.cmd` |

The installer prints the exact `install dir`, `venv dir`, `memory home`, and `env file` paths it selected.

Override the managed install paths when needed:

```bash
./scripts/install.sh --profile global --profile-confirmed --install-dir /path/to/mneme-runtime
./scripts/install.sh --profile global --profile-confirmed --venv-dir /path/to/mneme-venv
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed -InstallDir C:\path\to\mneme-runtime
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed -VenvDir C:\path\to\mneme-venv
```

The default installer performs a normal package install, so the runtime does not depend on keeping the repo checkout on your Desktop. Contributors can use editable mode:

```bash
./scripts/install.sh --profile global --profile-confirmed --editable
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed -Editable
```

## Agent Mesh

![Mneme agent bridge](assets/docs/agent-bridge.png)

Mneme makes Claude and Codex meet in the same memory field.

- Claude -> Codex: installed through OpenAI's `codex-plugin-cc` Claude Code plugin.
- Codex -> Claude: exposed through Mneme's `delegate_to_claude` MCP tool.
- Shared memory: both clients use the same Mneme MCP server pointed at the same Hermes-compatible memory home.
- Always-on continuity: global Claude/Codex instructions, Claude startup and per-prompt memory injection, and local capture hooks make chats consult shared memory and keep adding searchable context as work happens.
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

Automatic conversation captures are stored in SQLite as lower-trust `conversation` facts. They are searchable by Mneme but are not appended to `USER.md` or `MEMORY.md`, which keeps the always-loaded Markdown memory small and intentional.

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
- `mneme-memory-capture` - index local Claude/Codex conversation transcripts into searchable memory
- `mneme-memory-continuity` - install or inspect always-on Claude/Codex memory continuity
- `mneme-memory-env-mcp` - run the MCP server after loading memory settings from a `.env` file

## Manual Install

macOS / Linux:

```bash
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

Windows:

```powershell
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Your server command will be:

```bash
/absolute/path/to/mneme-memory-mcp/.venv/bin/mneme-memory-mcp
```

On Windows:

```text
C:\absolute\path\to\mneme-memory-mcp\.venv\Scripts\python.exe -m mneme_memory_mcp
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

On Windows, use TOML literal strings so backslashes are not interpreted as escapes:

```toml
[mcp_servers.mneme_memory]
command = 'C:\absolute\path\to\mneme-memory-mcp\.venv\Scripts\python.exe'
args = ['-m', 'mneme_memory_mcp']
startup_timeout_sec = 120

[mcp_servers.mneme_memory.env]
HERMES_HOME = 'C:\Users\YOU\.hermes'
```

Restart Codex or open a fresh session so it reloads MCP servers.

Example config files live in `examples/codex-config.toml` and `examples/codex-config-windows.toml`.

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

On Windows:

```json
{
  "mcpServers": {
    "mneme-memory": {
      "type": "stdio",
      "command": "C:\\absolute\\path\\to\\mneme-memory-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mneme_memory_mcp"],
      "env": {
        "HERMES_HOME": "C:\\Users\\YOU\\.hermes"
      }
    }
  }
}
```

If you already have other `mcpServers`, merge the `mneme-memory` entry into the existing object.

Example config files live in `examples/claude.json` and `examples/claude-windows.json`.

## Always-On Client Memory

Always-on client memory is the `global` profile. It is ideal for one trusted personal machine, because every configured local Claude and Codex session is instructed to start from the same memory layer.

The installer writes managed instruction blocks to:

- `~/.codex/AGENTS.md`
- `~/.claude/CLAUDE.md`

It also installs this Claude Code hook:

```text
~/.claude/hooks/mneme-memory-sessionstart.sh
```

On Windows this hook is:

```text
%USERPROFILE%\.claude\hooks\mneme-memory-sessionstart.cmd
```

and merges it into `~/.claude/settings.json` under `SessionStart`.

The MCP server is still the source of truth for search and writes; the global instructions plus Claude startup and per-prompt hooks make high-signal memory visible in fresh chats and before future prompts in active Claude Code sessions.

Read the full behavior in [docs/always-on-memory.md](docs/always-on-memory.md).

For repo-scoped memory, choose the `project` profile when prompted, or use `--profile project --profile-confirmed` after the user has chosen it. That profile configures MCP clients through `mneme-memory-env-mcp`, which reads `MNEME_HOME` or `HERMES_HOME` from `.env`, and it does not install global Claude/Codex memory instructions.

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
