# Agent Mesh

![Mneme agent bridge](../assets/docs/agent-bridge.png)

Mneme is the shared memory layer and the bridge surface between local agents.

The all-in-one installer wires six pieces:

1. Hermes-compatible local memory in `~/.hermes`
2. Mneme MCP in Codex and Claude Code
3. OpenAI's Claude Code plugin for Claude -> Codex delegation
4. Mneme's MCP bridge tools for Codex -> Claude delegation
5. Ponytail for smaller, safer code-generation behavior in both clients
6. Always-on memory instructions so fresh Claude and Codex chats start from shared memory

## Install

```bash
./scripts/install.sh
```

The installer is best-effort for client setup. If a client CLI is missing, Mneme still installs and prints manual fallback config.

Use this when you only want the memory server:

```bash
./scripts/install.sh --memory-only
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

![Mneme cross-chat continuity](../assets/docs/cross-chat-continuity.png)

Both clients point at the same server command:

```bash
/absolute/path/to/mneme-memory-mcp/.venv/bin/mneme-memory-mcp
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

The installer also writes managed Mneme continuity blocks into:

```text
~/.codex/AGENTS.md
~/.claude/CLAUDE.md
```

and configures a Claude Code `SessionStart` hook that injects USER.md and MEMORY.md into new Claude sessions.

That means fresh local Claude and Codex chats should begin by checking the same memory layer before answering, then keep improving the layer with durable memories when the user expects continuity.

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
