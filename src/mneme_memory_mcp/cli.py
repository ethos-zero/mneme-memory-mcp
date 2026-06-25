from __future__ import annotations

import argparse

from .store import MemoryCategory, MemoryScope, MemoryTarget, MemoryType, SharedMemoryStore, format_facts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mneme-memory",
        description="Read and write the shared Mneme/Hermes memory layer.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary", help="Print USER.md and MEMORY.md.")

    search = subparsers.add_parser("search", help="Search durable facts.")
    search.add_argument("query", help="Search terms.")
    search.add_argument("--limit", type=int, default=10, help="Maximum results.")
    search.add_argument(
        "--scope",
        choices=("global", "project", "agent-private", "handoff"),
        default="project",
        help="Read visibility scope.",
    )

    recent = subparsers.add_parser("list", help="List recent durable facts.")
    recent.add_argument("--limit", type=int, default=25, help="Maximum results.")
    recent.add_argument(
        "--scope",
        choices=("global", "project", "agent-private", "handoff"),
        default="project",
        help="Read visibility scope.",
    )

    add = subparsers.add_parser("add", help="Add a durable fact.")
    add.add_argument("content", nargs="+", help="Fact content to remember.")
    add.add_argument(
        "--target",
        choices=("user", "memory"),
        default="memory",
        help="Memory target file to append to.",
    )
    add.add_argument(
        "--category",
        choices=("user_pref", "project", "tool", "general", "conversation"),
        default="general",
        help="Fact category.",
    )
    add.add_argument("--tags", default="", help="Comma-separated tags.")
    add.add_argument(
        "--memory-type",
        choices=("semantic", "episodic", "procedural", "resource", "handoff"),
        default="semantic",
        help="Typed memory layer.",
    )
    add.add_argument(
        "--scope",
        choices=("global", "project", "agent-private", "handoff"),
        default=None,
        help="Memory visibility scope.",
    )
    add.add_argument("--key", default="", help="Stable supersession key for mutable facts.")
    add.add_argument("--version", default="", help="Optional version or freshness signal.")

    current = subparsers.add_parser("current", help="Resolve the current fact for a supersession key.")
    current.add_argument("key")
    current.add_argument(
        "--scope",
        choices=("global", "project", "agent-private", "handoff"),
        default="project",
        help="Read visibility scope.",
    )

    subparsers.add_parser("consolidate", help="Regenerate compact USER.md and MEMORY.md views.")

    handoff = subparsers.add_parser("handoff", help="Read or write structured handoffs.")
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_latest = handoff_sub.add_parser("latest", help="Print the latest handoff for a scope.")
    handoff_latest.add_argument("--scope", default="global")
    handoff_write = handoff_sub.add_parser("write", help="Write a structured handoff.")
    handoff_write.add_argument("--scope", default="global")
    handoff_write.add_argument("--goal", required=True)
    handoff_write.add_argument("--repo-state", default="")
    handoff_write.add_argument("--files-touched", default="")
    handoff_write.add_argument("--decisions", default="")
    handoff_write.add_argument("--blockers", default="")
    handoff_write.add_argument("--assumptions", default="")
    handoff_write.add_argument("--validation", default="")
    handoff_write.add_argument("--next-steps", default="")
    handoff_write.add_argument("--evidence", default="")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    store = SharedMemoryStore()

    if args.command == "summary":
        print(store.summary())
    elif args.command == "search":
        print(format_facts(store.search(query=args.query, limit=args.limit, scope=args.scope)))
    elif args.command == "list":
        print(format_facts(store.list(limit=args.limit, scope=args.scope)))
    elif args.command == "add":
        content = " ".join(args.content)
        fact_id = store.add(
            content=content,
            target=args.target,
            category=args.category,
            tags=args.tags,
            memory_type=args.memory_type,
            scope=args.scope,
            key=args.key,
            version=args.version,
        )
        print(f"saved fact {fact_id} to {args.target} memory")
    elif args.command == "current":
        fact = store.current(args.key, scope=args.scope)
        print(fact.format() if fact else "(no current fact)")
    elif args.command == "consolidate":
        store.consolidate()
        print("regenerated USER.md and MEMORY.md")
    elif args.command == "handoff":
        if args.handoff_command == "latest":
            handoff = store.latest_handoff(args.scope)
            print(handoff.format() if handoff else "(no handoff)")
        elif args.handoff_command == "write":
            handoff_id = store.write_handoff(
                scope=args.scope,
                goal=args.goal,
                repo_state=args.repo_state,
                files_touched=args.files_touched,
                decisions=args.decisions,
                blockers=args.blockers,
                assumptions=args.assumptions,
                validation=args.validation,
                next_steps=args.next_steps,
                evidence=args.evidence,
            )
            print(f"saved handoff {handoff_id}")


__all__ = [
    "build_parser",
    "main",
    "MemoryCategory",
    "MemoryScope",
    "MemoryTarget",
    "MemoryType",
]


if __name__ == "__main__":
    main()
