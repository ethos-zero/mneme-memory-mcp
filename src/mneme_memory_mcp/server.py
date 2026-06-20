from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from .store import SharedMemoryStore, format_facts

mcp = FastMCP("mneme-memory")


def store() -> SharedMemoryStore:
    return SharedMemoryStore()


@mcp.tool()
def memory_summary() -> str:
    """Return the always-on shared memory summary."""

    return store().summary()


@mcp.tool()
def memory_search(query: str, limit: int = 10) -> str:
    """Search the shared memory fact store."""

    return format_facts(store().search(query=query, limit=limit))


@mcp.tool()
def memory_list(limit: int = 25) -> str:
    """List recent facts from the shared memory fact store."""

    return format_facts(store().list(limit=limit))


@mcp.tool()
def memory_add(
    content: str,
    target: Literal["user", "memory"] = "memory",
    category: Literal["user_pref", "project", "tool", "general"] = "general",
    tags: str = "",
) -> str:
    """Add a durable fact to shared memory.

    Use target='user' for identity, preferences, and working style.
    Use target='memory' for projects, tools, paths, decisions, and setup notes.
    """

    try:
        fact_id = store().add(content=content, target=target, category=category, tags=tags)
    except ValueError as exc:
        return f"error: {exc}"
    return f"saved fact {fact_id} to {target} memory"


@mcp.tool()
def memory_update(
    fact_id: int,
    content: str | None = None,
    category: Literal["user_pref", "project", "tool", "general"] | None = None,
    tags: str | None = None,
    trust_score: float | None = None,
) -> str:
    """Update a fact by id."""

    ok = store().update(
        fact_id=fact_id,
        content=content,
        category=category,
        tags=tags,
        trust_score=trust_score,
    )
    return "updated" if ok else f"fact {fact_id} not found"


@mcp.tool()
def memory_remove(fact_id: int) -> str:
    """Remove a fact by id and remove the matching Markdown bullet if present."""

    ok = store().remove(fact_id=fact_id)
    return "removed" if ok else f"fact {fact_id} not found"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

