# Always-On Memory

![Mneme cross-chat continuity](../assets/docs/cross-chat-continuity.png)

Mneme can run in global mode or project/env-scoped mode.

Global mode is meant to make every configured agent answer from the same remembered ground. Project/env mode is meant to keep memory isolated to a repo or environment file.

The installer gives Claude Code and Codex a persistent memory habit in four layers:

1. Shared local memory files in `~/.hermes/memories`
2. Shared searchable facts in `~/.hermes/memory_store.db`
3. Mneme MCP tools in Claude and Codex
4. Global client instructions that tell new chats to consult Mneme before substantive answers

For Claude Code, Mneme adds a fifth layer: a `SessionStart` hook that prints the Markdown memory summary into every fresh Claude session.

## What Gets Installed

Running:

```bash
./scripts/install.sh --profile global
```

installs or updates managed Mneme blocks in:

```text
~/.codex/AGENTS.md
~/.claude/CLAUDE.md
```

The blocks tell each client to start from shared memory, prefer the Mneme MCP tools, and use the `mneme-memory` CLI fallback if MCP tools are unavailable.

Claude also gets:

```text
~/.claude/hooks/mneme-memory-sessionstart.sh
```

and a `SessionStart` hook entry in:

```text
~/.claude/settings.json
```

If an existing compatible Hermes/Mneme memory hook is already present, Mneme keeps it and avoids adding a duplicate.

## Project/Env-Scoped Memory

Use this when you want Mneme available to Claude and Codex, but you do not want global memory instructions or a machine-wide startup hook:

```bash
./scripts/install.sh --profile project
```

This profile reads memory settings from:

```text
.env
```

If the file does not contain `MNEME_HOME` or `HERMES_HOME`, the installer adds a project-local default:

```env
MNEME_HOME=/absolute/path/to/mneme-memory-mcp/.mneme
```

Claude and Codex are configured to run:

```bash
mneme-memory-env-mcp --env-file /path/to/.env --default-home /path/to/.mneme
```

That launcher loads the `.env` memory settings when the MCP server starts. It does not write to `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`, or Claude `SessionStart` hooks.

## The Memory-First Rule

Fresh Claude and Codex chats should follow this order:

1. Read `memory_summary` for USER.md and MEMORY.md context.
2. Use `memory_search` when prior work, preferences, repo state, tools, people, or decisions may matter.
3. Add durable facts with `memory_add` when the user would reasonably expect future agents to remember them.
4. Fall back to the local CLI when MCP tools are not available:

```bash
mneme-memory summary
mneme-memory search "query terms"
mneme-memory add --target memory "durable fact"
```

## Doctor Check

Check the continuity layer with:

```bash
.venv/bin/mneme-memory-doctor
```

or directly:

```bash
.venv/bin/mneme-memory-continuity status
```

Expected healthy output includes:

```text
Codex always-on memory instructions: ok
Claude always-on memory instructions: ok
Claude SessionStart memory hook file: ok
Claude SessionStart memory hook configured: ok
```

## Practical Guarantee

Mneme can make the memory layer the default for configured Claude Code and Codex clients by installing global instructions, MCP servers, a CLI fallback, and the Claude startup hook.

No package can force an unconfigured client, a client that ignores its global instructions, or a disconnected remote chat to read local files. But once the installer has run successfully on a machine, new local Claude Code and Codex chats have the shared memory layer wired in by default.

## Opt Out

Skip the continuity layer while keeping MCP/plugin setup:

```bash
./scripts/install.sh --no-continuity
```

Install only the memory server without client or plugin changes:

```bash
./scripts/install.sh --memory-only
```

Install with project/env-scoped memory instead of global memory:

```bash
./scripts/install.sh --profile project
```
