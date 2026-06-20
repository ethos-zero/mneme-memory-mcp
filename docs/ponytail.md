# Ponytail Integration

![Mneme MCP tool constellation](../assets/docs/mcp-tool-constellation.png)

Mneme's installer integrates [Ponytail](https://github.com/DietrichGebert/ponytail) as the code-efficiency layer for Claude Code and Codex.

Ponytail is not vendored into Mneme. It remains an upstream plugin, installed from its own marketplace so users receive its current skills, commands, and lifecycle hooks.

## Visual Idea

![Ponytail Ladder](../assets/docs/ponytail-ladder.png)

Ponytail is the ladder Mneme gives the agent loop before it writes code: skip what does not need to exist, use the platform when it already solves the problem, and leave one clean line where a pile of scaffolding wanted to grow.

![Less Code, Same Memory](../assets/docs/less-code-same-memory.png)

Claude and Codex still meet at the same memory layer. Ponytail keeps that loop from turning every task into an architecture ceremony.

## What Mneme Installs

For Claude Code:

```bash
claude plugin marketplace add DietrichGebert/ponytail
claude plugin install -s user ponytail@ponytail
```

For Codex:

```bash
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

If either CLI is missing, the installer skips that client and keeps going.

## Why It Belongs Here

Mneme gives agents memory and a bridge. Ponytail gives them a shared engineering bias:

- YAGNI before scaffolding
- standard library before custom code
- native platform before dependencies
- one clear solution before a framework-shaped one
- safety checks preserved where they matter

That makes the Claude/Codex loop less noisy. The agents can ask each other for help without amplifying boilerplate.

## Turning It Off

To install Mneme without Ponytail or other agent plugins:

```bash
./scripts/install.sh --no-agent-plugins
```

To install only the memory server:

```bash
./scripts/install.sh --memory-only
```

## Source

Ponytail is MIT licensed and maintained at:

```text
https://github.com/DietrichGebert/ponytail
```
