from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .continuity import continuity_status
from .store import resolve_db_path, resolve_home, resolve_memory_dir


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path
    return None


def find_hermes() -> str | None:
    found = shutil.which("hermes")
    if found:
        return found

    candidates = [
        Path.home() / ".local" / "bin" / "hermes",
        Path.home() / ".hermes" / "bin" / "hermes",
        Path.home() / ".hermes" / "hermes-agent" / "hermes",
    ]
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        candidates.extend(
            [
                Path.home() / ".local" / "bin" / "hermes.exe",
                Path.home() / ".hermes" / "bin" / "hermes.exe",
                Path.home() / ".hermes" / "hermes-agent" / "hermes.exe",
            ]
        )
        if local_app_data:
            candidates.append(
                Path(local_app_data)
                / "hermes"
                / "hermes-agent"
                / "venv"
                / "Scripts"
                / "hermes.exe"
            )
    existing = _first_existing(candidates)
    return str(existing) if existing else None


def _which(command: str) -> str:
    return shutil.which(command) or "missing"


def _version(command: str) -> str:
    try:
        result = subprocess.run(
            [command, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return "version unavailable"

    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if text else "version unavailable"


def status_lines() -> list[str]:
    home = resolve_home()
    memory_dir = resolve_memory_dir(home)
    db_path = resolve_db_path(home)
    hermes = find_hermes()

    lines = [
        "Mneme Memory MCP doctor",
        "",
        f"memory home: {home}",
        f"markdown memories: {memory_dir}",
        f"fact store: {db_path}",
        f"USER.md: {'ok' if (memory_dir / 'USER.md').exists() else 'missing'}",
        f"MEMORY.md: {'ok' if (memory_dir / 'MEMORY.md').exists() else 'missing'}",
        f"SQLite store: {'ok' if db_path.exists() else 'will be created on first write'}",
        f"Claude CLI: {_which('claude')}",
        f"Codex CLI: {_which('codex')}",
        f"Node: {_which('node')}",
    ]

    if hermes:
        lines.append(f"Hermes Agent: {hermes} ({_version(hermes)})")
    else:
        lines.append("Hermes Agent: missing")
        if os.name == "nt":
            lines.append("Hermes auto-install is not available on Windows; Mneme MCP memory can still run without Hermes.")
        else:
            lines.append("Install Hermes with: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash")

    lines.extend(["", "Always-on memory continuity:"])
    lines.extend(f"  {line}" for line in continuity_status().lines())

    lines.extend(
        [
            "",
            "MCP server command:",
            "  mneme-memory-mcp",
        ]
    )
    return lines


def main() -> None:
    print("\n".join(status_lines()))


if __name__ == "__main__":
    main()
