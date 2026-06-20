# Hermes Pairing

![Mneme local-first store](../assets/docs/local-first-store.png)

Mneme is built for the Hermes memory shape.

Hermes Agent gives you the local agent runtime. Mneme gives Claude, Codex, Hermes, and other MCP clients a small shared-memory server pointed at the same durable home.

```text
Claude Code  -----\
Codex          ----- mneme-memory-mcp ----- ~/.hermes
Hermes Agent  -----/                          memories/ + memory_store.db
```

## Install Everything

```bash
git clone https://github.com/ethos-zero/mneme-memory-mcp.git
cd mneme-memory-mcp
./scripts/install.sh
```

If Hermes Agent is missing, the installer runs the official Hermes installer:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Use this when Hermes is already installed or you want to manage it yourself:

```bash
./scripts/install.sh --no-hermes-install
```

## What Gets Created

- `~/.hermes/memories/USER.md`
- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memory_store.db`
- `.venv/bin/mneme-memory-mcp`
- `.venv/bin/mneme-memory-doctor`

## Check The Setup

```bash
.venv/bin/mneme-memory-doctor
```

The doctor checks:

- where the shared memory home resolves
- whether Markdown memory files exist
- whether the SQLite fact store exists
- whether Hermes Agent is installed
- the MCP server command to use

## Connect MCP Clients

Codex:

```toml
[mcp_servers.mneme_memory]
command = "/absolute/path/to/mneme-memory-mcp/.venv/bin/mneme-memory-mcp"
args = []
startup_timeout_sec = 120

[mcp_servers.mneme_memory.env]
HERMES_HOME = "/Users/YOU/.hermes"
```

Claude Code:

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

Hermes Agent MCP server, if you want the Hermes runtime exposed beside Mneme:

```toml
[mcp_servers.hermes]
command = "hermes"
args = ["mcp", "serve", "--accept-hooks"]
startup_timeout_sec = 120
```

## The Rule

Hermes is the local agent environment.

Mneme is the memory bridge.

Together, they give every connected agent one persistent layer to remember through.

![Mneme recall search](../assets/docs/recall-search.png)
