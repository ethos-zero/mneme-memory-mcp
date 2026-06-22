from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .store import SharedMemoryStore, resolve_home

AgentName = Literal["claude", "codex"]

DEFAULT_TIMEOUT_SECONDS = 600
MAX_CONTEXT_CHARS = 12000


@dataclass(frozen=True)
class AgentRun:
    agent: str
    command: list[str]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str

    def format(self) -> str:
        cmd = " ".join(self.command)
        pieces = [
            f"agent: {self.agent}",
            f"cwd: {self.cwd}",
            f"exit: {self.returncode}",
            f"command: {cmd}",
            "",
            (self.stdout or "").strip() or "(no stdout)",
        ]
        stderr = (self.stderr or "").strip()
        if stderr:
            pieces.extend(["", "stderr:", stderr])
        return "\n".join(pieces).strip()


def bridge_status() -> str:
    """Return local agent bridge readiness."""

    lines = [
        "Mneme agent bridge status",
        f"memory home: {resolve_home()}",
        f"claude: {_binary_status('claude')}",
        f"codex: {_binary_status('codex')}",
        f"node: {_binary_status('node')}",
    ]
    return "\n".join(lines)


def delegate_to_claude(
    prompt: str,
    cwd: str | None = None,
    model: str | None = None,
    permission_mode: str = "default",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> AgentRun:
    """Run a one-shot Claude Code task with Mneme memory injected."""

    prompt = _require_prompt(prompt)
    workdir = _resolve_cwd(cwd)
    claude = _require_binary("claude")
    command = [
        claude,
        "-p",
        "--permission-mode",
        permission_mode or "default",
        "--append-system-prompt",
        _mneme_system_prompt("Claude Code"),
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return _run("claude", command, workdir, timeout_seconds)


def delegate_to_codex(
    prompt: str,
    cwd: str | None = None,
    model: str | None = None,
    sandbox: Literal["read-only", "workspace-write", "danger-full-access"] = "workspace-write",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> AgentRun:
    """Run a one-shot Codex task with Mneme memory injected."""

    prompt = _require_prompt(prompt)
    workdir = _resolve_cwd(cwd)
    codex = _require_binary("codex")
    command = [
        codex,
        "exec",
        "-C",
        str(workdir),
        "--sandbox",
        sandbox,
        "--skip-git-repo-check",
        "--color",
        "never",
    ]
    if model:
        command.extend(["--model", model])
    command.append(_with_memory_prompt(prompt, "Codex"))
    return _run("codex", command, workdir, timeout_seconds)


def _binary_status(name: str) -> str:
    path = shutil.which(name)
    return path if path else "missing"


def _require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} CLI was not found on PATH")
    return path


def _require_prompt(prompt: str) -> str:
    prompt = str(prompt or "").strip()
    if not prompt:
        raise ValueError("prompt must not be empty")
    return prompt


def _resolve_cwd(cwd: str | None) -> Path:
    path = Path(cwd or os.getcwd()).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"cwd does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"cwd is not a directory: {path}")
    return path


def _bounded_timeout(timeout_seconds: int) -> int:
    try:
        value = int(timeout_seconds)
    except (TypeError, ValueError):
        value = DEFAULT_TIMEOUT_SECONDS
    return max(5, min(value, 3600))


def _mneme_system_prompt(agent_label: str) -> str:
    summary = SharedMemoryStore().summary()
    if len(summary) > MAX_CONTEXT_CHARS:
        summary = summary[:MAX_CONTEXT_CHARS] + "\n\n[Mneme memory summary truncated]"
    return (
        "You are being invoked through Mneme Memory MCP as "
        f"{agent_label}. Treat this as a peer-agent delegation.\n\n"
        "Use the shared Mneme/Hermes memory below for continuity. "
        "If durable facts are discovered, ask the caller to store them through Mneme memory tools.\n\n"
        f"{summary}"
    )


def _with_memory_prompt(prompt: str, agent_label: str) -> str:
    return f"{_mneme_system_prompt(agent_label)}\n\nDelegated task:\n{prompt}"


def _run(agent: str, command: list[str], cwd: Path, timeout_seconds: int) -> AgentRun:
    command = _windows_batch_safe_command(command)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=_bounded_timeout(timeout_seconds),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return AgentRun(
            agent=agent,
            command=command,
            cwd=cwd,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"timed out after {_bounded_timeout(timeout_seconds)} seconds",
        )

    return AgentRun(
        agent=agent,
        command=command,
        cwd=cwd,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _windows_batch_safe_command(command: list[str]) -> list[str]:
    if os.name != "nt" or not command:
        return command
    if Path(command[0]).suffix.lower() not in {".bat", ".cmd"}:
        return command
    return [command[0], *[_line_safe_arg(arg) for arg in command[1:]]]


def _line_safe_arg(arg: str) -> str:
    return str(arg).replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
