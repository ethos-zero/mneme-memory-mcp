from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .store import Fact, SharedMemoryStore

MAX_CONTEXT_CHARS = 12000
MAX_SUMMARY_CHARS = 7000
MAX_FACT_CHARS = 1200


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mneme-memory-hook-context",
        description="Emit Mneme memory context for Claude Code hooks.",
    )
    parser.add_argument("--memory-home", type=Path, default=None)
    parser.add_argument("--event", default=None)
    parser.add_argument("--recent-limit", type=int, default=8)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    payload = _read_hook_payload()
    event = args.event or str(payload.get("hook_event_name") or "UserPromptSubmit")
    store = SharedMemoryStore(home=args.memory_home) if args.memory_home else SharedMemoryStore()
    context = build_context(store=store, recent_limit=args.recent_limit)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": context,
                }
            },
            ensure_ascii=False,
        )
    )


def build_context(*, store: SharedMemoryStore, recent_limit: int = 8) -> str:
    parts = [
        "## Mneme Shared Persistent Memory",
        "Use this global memory before answering. It is shared by Claude, Codex, Hermes, and other configured local agents.",
        "",
        _truncate(store.summary(), MAX_SUMMARY_CHARS),
    ]
    recent = _recent_facts(store, recent_limit)
    if recent:
        parts.extend(["", "## Recent Searchable Facts", *[_format_fact(fact) for fact in recent]])
    return _truncate("\n".join(parts).strip(), MAX_CONTEXT_CHARS)


def _recent_facts(store: SharedMemoryStore, limit: int) -> list[Fact]:
    facts = store.list(limit=max(limit * 3, limit))
    kept = [fact for fact in facts if fact.category != "conversation"][:limit]
    remaining = limit - len(kept)
    if remaining <= 0:
        return kept
    conversation_limit = min(2, remaining)
    kept.extend(fact for fact in facts if fact.category == "conversation" and fact not in kept)
    return kept[: limit - remaining + conversation_limit]


def _format_fact(fact: Fact) -> str:
    content = _truncate(fact.content, MAX_FACT_CHARS)
    return f"- {content} [{fact.category}; tags={fact.tags}]"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 18)].rstrip() + "\n[truncated]"


def _read_hook_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


if __name__ == "__main__":
    main()
