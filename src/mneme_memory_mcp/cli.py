from __future__ import annotations

import argparse

from .store import MemoryCategory, MemoryTarget, SharedMemoryStore, format_facts


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

    recent = subparsers.add_parser("list", help="List recent durable facts.")
    recent.add_argument("--limit", type=int, default=25, help="Maximum results.")

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
        choices=("user_pref", "project", "tool", "general"),
        default="general",
        help="Fact category.",
    )
    add.add_argument("--tags", default="", help="Comma-separated tags.")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    store = SharedMemoryStore()

    if args.command == "summary":
        print(store.summary())
    elif args.command == "search":
        print(format_facts(store.search(query=args.query, limit=args.limit)))
    elif args.command == "list":
        print(format_facts(store.list(limit=args.limit)))
    elif args.command == "add":
        content = " ".join(args.content)
        fact_id = store.add(
            content=content,
            target=args.target,
            category=args.category,
            tags=args.tags,
        )
        print(f"saved fact {fact_id} to {args.target} memory")


__all__ = ["build_parser", "main", "MemoryCategory", "MemoryTarget"]


if __name__ == "__main__":
    main()
