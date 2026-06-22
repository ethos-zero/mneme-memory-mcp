# Agent Mesh

![Mneme agent bridge](../assets/docs/agent-bridge.png)

Mneme is the shared memory layer and the bridge surface between local agents.

With the `global` profile, the all-in-one installer wires six pieces:

1. Hermes-compatible local memory in `~/.hermes`
2. Mneme MCP in Codex and Claude Code
3. OpenAI's Claude Code plugin for Claude -> Codex delegation
4. Mneme's MCP bridge tools for Codex -> Claude delegation
5. Ponytail for smaller, safer code-generation behavior in both clients
6. Always-on memory instructions and Claude per-prompt hooks so chats keep seeing shared memory

With the `project` profile, Mneme still wires the MCP server and optional agent plugins, but memory comes from `.env` and global Claude/Codex memory instructions are skipped.

## Install

```bash
./scripts/install.sh
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

These commands prompt for `global`, `project`, or `server` setup. Non-interactive callers must stop and ask the user which profile they want, then rerun with `--profile`/`-Profile` plus `--profile-confirmed`/`-ProfileConfirmed`.

The installer is best-effort for client setup. If a client CLI is missing, Mneme still installs and prints manual fallback config.

Use this when you only want the memory server:

```bash
./scripts/install.sh --profile global --profile-confirmed --memory-only
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Profile global -ProfileConfirmed -MemoryOnly
```

## Claude To Codex

Mneme installs OpenAI's `codex-plugin-cc` marketplace into Claude Code when the `claude` CLI is available:

```bash
claude plugin marketplace add openai/codex-plugin-cc
claude plugin install -s user codex@openai-codex
```

That plugin gives Claude Code slash commands like `/codex:review`, `/codex:rescue`, `/codex:status`, and `/codex:result`.

## Codex To Claude

Mneme exposes `delegate_to_claude` as an MCP tool. Codex can call it when Claude should take a pass at a task.

The tool invokes:

```bash
claude -p --append-system-prompt "<Mneme memory summary>" "<task>"
```

The delegated Claude call receives the current Mneme memory summary, so it starts with the same continuity layer even in one-shot mode.

## Shared Memory

Both clients point at the same server command:

```bash
/Users/YOU/.local/share/mneme-memory-mcp/venv/bin/mneme-memory-mcp
```

On Windows:

```text
C:\Users\YOU\AppData\Local\mneme-memory-mcp\venv\Scripts\python.exe -m mneme_memory_mcp
```

And the same memory home:

```bash
HERMES_HOME="$HOME/.hermes"
```

That home contains:

```text
~/.hermes/memories/USER.md
~/.hermes/memories/MEMORY.md
~/.hermes/memory_store.db
```

On Windows, `~` resolves to `%USERPROFILE%`, so the default memory home is `%USERPROFILE%\.hermes` unless `MNEME_HOME` or `HERMES_HOME` is set.

The installer also writes managed Mneme continuity blocks into:

```text
~/.codex/AGENTS.md
~/.claude/CLAUDE.md
```

On Windows these live under `%USERPROFILE%\.codex` and `%USERPROFILE%\.claude`.

and configures local hooks that keep the shared memory alive across fresh sessions:

- Claude `SessionStart` injects USER.md and MEMORY.md for fresh sessions.
- Claude `UserPromptSubmit` injects shared memory context before future prompts.
- Claude `Stop` and `SessionEnd` index recent transcript snippets into Mneme search.
- Codex `notify` is wrapped so each turn can index recent Codex transcript snippets, then forward to the previous notify command.

That means fresh local Claude and Codex chats should begin by checking the same memory layer before answering, then keep improving the layer through durable memories and searchable conversation capture.

More details live in [always-on-memory.md](always-on-memory.md).

## Bridge Tools

| Tool | Use |
| --- | --- |
| `agent_bridge_status` | Show whether `claude`, `codex`, and `node` are available |
| `delegate_to_claude` | Ask Claude Code for a one-shot peer pass |
| `delegate_to_codex` | Ask Codex for a one-shot peer pass |

`delegate_to_codex` is available as a Mneme fallback, but Claude Code users should prefer the richer OpenAI `codex-plugin-cc` commands when available.

## Safety

Only connect agents you trust. Mneme is local-first, but any connected agent can read and write the configured local memory.

The bridge tools run local CLIs as subprocesses. `delegate_to_codex` defaults to Codex `workspace-write` sandboxing with non-interactive approvals disabled, because MCP tool calls cannot answer approval prompts. Use `sandbox="read-only"` for review-only delegation.
