from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MemoryTarget = Literal["user", "memory"]
MemoryCategory = Literal["user_pref", "project", "tool", "general"]


def resolve_home() -> Path:
    """Resolve the shared memory home directory.

    Environment priority:
    1. MNEME_HOME
    2. HERMES_HOME
    3. ~/.hermes
    """

    raw = (
        os.environ.get("MNEME_HOME")
        or os.environ.get("HERMES_HOME")
        or "~/.hermes"
    )
    return Path(raw).expanduser()


def resolve_memory_dir(home: Path | None = None) -> Path:
    raw = os.environ.get("MNEME_MEMORY_DIR")
    if raw:
        return Path(raw).expanduser()
    return (home or resolve_home()) / "memories"


def resolve_db_path(home: Path | None = None) -> Path:
    raw = os.environ.get("MNEME_DB_PATH")
    if raw:
        return Path(raw).expanduser()
    return (home or resolve_home()) / "memory_store.db"


@dataclass(frozen=True)
class Fact:
    fact_id: int
    content: str
    category: str
    tags: str
    trust_score: float

    def format(self) -> str:
        return (
            f"{self.fact_id} [{self.category}; trust={self.trust_score:.2f}; "
            f"tags={self.tags}]: {self.content}"
        )


class SharedMemoryStore:
    """Local Markdown + SQLite memory store.

    The Markdown files provide always-on context for humans and agents:
    - USER.md for user identity and preferences
    - MEMORY.md for projects, paths, decisions, and tool setup

    The SQLite database provides searchable facts through FTS5.
    """

    def __init__(
        self,
        home: Path | None = None,
        memory_dir: Path | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.home = home or resolve_home()
        self.memory_dir = memory_dir or resolve_memory_dir(self.home)
        self.db_path = db_path or resolve_db_path(self.home)
        self.user_file = self.memory_dir / "USER.md"
        self.memory_file = self.memory_dir / "MEMORY.md"

    def ensure(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def read_markdown(self, target: MemoryTarget) -> str:
        path = self._target_path(target)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def summary(self) -> str:
        user = self.read_markdown("user") or "(empty)"
        memory = self.read_markdown("memory") or "(empty)"
        return f"# USER.md\n{user}\n\n# MEMORY.md\n{memory}"

    def add(
        self,
        content: str,
        target: MemoryTarget = "memory",
        category: MemoryCategory = "general",
        tags: str = "",
    ) -> int:
        content = _normalize_content(content)
        if not content:
            raise ValueError("content must not be empty")

        self.ensure()
        self._append_markdown(target, content)
        return self._insert_fact(content, category, tags)

    def list(self, limit: int = 25) -> list[Fact]:
        self.ensure()
        limit = _bounded_limit(limit, upper=100)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT fact_id, content, category, tags, trust_score
                FROM facts
                ORDER BY fact_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def search(self, query: str, limit: int = 10) -> list[Fact]:
        self.ensure()
        query = query.strip()
        if not query:
            return []
        limit = _bounded_limit(limit, upper=25)
        with self.connect() as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT f.fact_id, f.content, f.category, f.tags, f.trust_score
                    FROM facts f
                    JOIN facts_fts fts ON fts.rowid = f.fact_id
                    WHERE facts_fts MATCH ?
                    ORDER BY fts.rank, f.trust_score DESC
                    LIMIT ?
                    """,
                    (_fts_query(query), limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = conn.execute(
                    """
                    SELECT fact_id, content, category, tags, trust_score
                    FROM facts
                    WHERE lower(content) LIKE lower(?)
                       OR lower(tags) LIKE lower(?)
                       OR lower(category) LIKE lower(?)
                    ORDER BY trust_score DESC, fact_id DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", f"%{query}%", limit),
                ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def update(
        self,
        fact_id: int,
        content: str | None = None,
        category: MemoryCategory | None = None,
        tags: str | None = None,
        trust_score: float | None = None,
    ) -> bool:
        self.ensure()
        current = self._get_fact(fact_id)
        if current is None:
            return False

        new_content = _normalize_content(content) if content is not None else current.content
        new_category = category or current.category
        new_tags = tags if tags is not None else current.tags
        new_trust = (
            max(0.0, min(1.0, float(trust_score)))
            if trust_score is not None
            else current.trust_score
        )

        with self.connect() as conn:
            conn.execute(
                """
                UPDATE facts
                SET content = ?, category = ?, tags = ?, trust_score = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE fact_id = ?
                """,
                (new_content, new_category, new_tags, new_trust, fact_id),
            )
            conn.commit()

        if content is not None and new_content != current.content:
            self._replace_markdown_entry(current.content, new_content)
        return True

    def remove(self, fact_id: int) -> bool:
        self.ensure()
        current = self._get_fact(fact_id)
        if current is None:
            return False
        with self.connect() as conn:
            conn.execute("DELETE FROM facts WHERE fact_id = ?", (fact_id,))
            conn.commit()
        self._remove_markdown_entry(current.content)
        return True

    def _get_fact(self, fact_id: int) -> Fact | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT fact_id, content, category, tags, trust_score
                FROM facts
                WHERE fact_id = ?
                """,
                (fact_id,),
            ).fetchone()
        return _row_to_fact(row) if row else None

    def _insert_fact(self, content: str, category: str, tags: str) -> int:
        with self.connect() as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO facts (content, category, tags, trust_score)
                    VALUES (?, ?, ?, 0.65)
                    """,
                    (content, category, tags),
                )
                conn.commit()
                return int(cur.lastrowid)
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT fact_id FROM facts WHERE content = ?",
                    (content,),
                ).fetchone()
                return int(row["fact_id"])

    def _target_path(self, target: MemoryTarget) -> Path:
        return self.user_file if target == "user" else self.memory_file

    def _append_markdown(self, target: MemoryTarget, content: str) -> None:
        path = self._target_path(target)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        bullet = f"- {content}"
        if bullet in {line.strip() for line in existing.splitlines()}:
            return
        with path.open("a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(f"{bullet}\n")

    def _replace_markdown_entry(self, old: str, new: str) -> None:
        for path in (self.user_file, self.memory_file):
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            replaced = text.replace(f"- {old}", f"- {new}")
            if replaced != text:
                path.write_text(replaced, encoding="utf-8")

    def _remove_markdown_entry(self, content: str) -> None:
        for path in (self.user_file, self.memory_file):
            if not path.exists():
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            kept = [line for line in lines if line.strip() != f"- {content}"]
            if kept != lines:
                path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")


SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT 'general',
    tags TEXT DEFAULT '',
    trust_score REAL DEFAULT 0.5,
    retrieval_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
    USING fts5(content, tags, content=facts, content_rowid=fact_id);

CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, content, tags)
        VALUES (new.fact_id, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content, tags)
        VALUES ('delete', old.fact_id, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content, tags)
        VALUES ('delete', old.fact_id, old.content, old.tags);
    INSERT INTO facts_fts(rowid, content, tags)
        VALUES (new.fact_id, new.content, new.tags);
END;
"""


def format_facts(facts: list[Fact]) -> str:
    if not facts:
        return "(no matches)"
    return "\n".join(fact.format() for fact in facts)


def _row_to_fact(row: sqlite3.Row) -> Fact:
    return Fact(
        fact_id=int(row["fact_id"]),
        content=str(row["content"]),
        category=str(row["category"]),
        tags=str(row["tags"] or ""),
        trust_score=float(row["trust_score"]),
    )


def _normalize_content(content: str | None) -> str:
    return re.sub(r"\s+", " ", (content or "").strip())


def _bounded_limit(limit: int, upper: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 10
    return max(1, min(value, upper))


def _fts_query(query: str) -> str:
    # FTS5 treats whitespace as AND, which is fine, but punctuation-heavy
    # user queries can throw. Keep simple words and quote each one.
    terms = re.findall(r"[A-Za-z0-9_]+", query)
    if not terms:
        return query
    return " ".join(f'"{term}"' for term in terms)
