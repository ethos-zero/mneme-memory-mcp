from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MemoryTarget = Literal["user", "memory"]
MemoryCategory = Literal["user_pref", "project", "tool", "general", "conversation"]
MemoryType = Literal["semantic", "episodic", "procedural", "resource", "handoff"]
MemoryScope = Literal["global", "project", "agent-private", "handoff"]

GENERATED_HEADER = "<!-- mneme-generated-start -->"
GENERATED_FOOTER = "<!-- mneme-generated-end -->"


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
    memory_type: str = "semantic"
    scope: str = "global"
    key: str = ""
    version: str = ""
    source: str = "manual"
    provenance: str = ""

    def format(self) -> str:
        key = f"; key={self.key}" if self.key else ""
        version = f"; version={self.version}" if self.version else ""
        return (
            f"{self.fact_id} [{self.memory_type}/{self.scope}; {self.category}; "
            f"trust={self.trust_score:.2f}{key}{version}; tags={self.tags}]: {self.content}"
        )


@dataclass(frozen=True)
class Handoff:
    handoff_id: int
    scope: str
    goal: str
    repo_state: str
    files_touched: str
    decisions: str
    blockers: str
    assumptions: str
    validation: str
    next_steps: str
    evidence: str
    created_at: str

    def format(self) -> str:
        parts = [
            f"handoff {self.handoff_id} [{self.scope}]",
            f"goal: {self.goal}",
            f"repo_state: {self.repo_state}",
            f"files_touched: {self.files_touched}",
            f"decisions: {self.decisions}",
            f"blockers: {self.blockers}",
            f"assumptions: {self.assumptions}",
            f"validation: {self.validation}",
            f"next_steps: {self.next_steps}",
            f"evidence: {self.evidence}",
            f"created_at: {self.created_at}",
        ]
        return "\n".join(parts)


class SharedMemoryStore:
    """Local Markdown + SQLite memory store.

    The SQLite event/fact store is the ground truth. USER.md and MEMORY.md are
    compact generated views for always-loaded context.
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
        with closing(self.connect()) as conn:
            conn.executescript(SCHEMA)
            _migrate(conn)
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
        self.ensure()
        user = self.read_markdown("user") or "(empty)"
        memory = self.read_markdown("memory") or "(empty)"
        return f"# USER.md\n{user}\n\n# MEMORY.md\n{memory}"

    def add(
        self,
        content: str,
        target: MemoryTarget = "memory",
        category: MemoryCategory = "general",
        tags: str = "",
        memory_type: MemoryType = "semantic",
        scope: MemoryScope | None = None,
        key: str = "",
        version: str = "",
    ) -> int:
        if target == "user" and category == "general":
            category = "user_pref"
        fact_id = self.add_fact(
            content=content,
            target=target,
            category=category,
            tags=tags,
            append_markdown=False,
            memory_type=memory_type,
            scope=scope or ("global" if target == "user" else "project"),
            key=key,
            version=version,
        )
        self.consolidate()
        return fact_id

    def add_fact(
        self,
        content: str,
        target: MemoryTarget = "memory",
        category: MemoryCategory = "general",
        tags: str = "",
        append_markdown: bool = False,
        trust_score: float = 0.65,
        memory_type: MemoryType = "semantic",
        scope: MemoryScope = "global",
        key: str = "",
        version: str = "",
        source: str = "manual",
    ) -> int:
        content = _normalize_content(content)
        if not content:
            raise ValueError("content must not be empty")

        self.ensure()
        event_id = self._insert_event(
            event_type="fact.add",
            scope=scope,
            source=source,
            content=content,
            trust_score=trust_score,
        )
        fact_id = self._insert_fact(
            content,
            category,
            tags,
            trust_score=trust_score,
            memory_type=memory_type,
            scope=scope,
            key=_normalize_key(key),
            version=version,
            source=source,
            provenance=f"event:{event_id}",
        )
        self._update_event_ref(event_id, "facts", fact_id)
        if append_markdown:
            self.consolidate()
        return fact_id

    def add_event(
        self,
        *,
        event_type: str,
        scope: str = "global",
        source: str = "manual",
        content: str = "",
        ref_table: str = "",
        ref_id: int | None = None,
        trust_score: float = 0.5,
    ) -> int:
        self.ensure()
        event_id = self._insert_event(
            event_type=event_type,
            scope=scope,
            source=source,
            content=content,
            ref_table=ref_table,
            ref_id=ref_id,
            trust_score=trust_score,
        )
        return event_id

    def add_episodic(
        self,
        *,
        source: str,
        session_id: str,
        role: str,
        text: str,
        tags: str = "",
        trust_score: float = 0.30,
    ) -> int:
        text = _normalize_content(text)
        if not text:
            raise ValueError("text must not be empty")
        self.ensure()
        event_id = self._insert_event(
            event_type="episodic.add",
            scope="global",
            source=source,
            content=f"{session_id} {role}: {text[:240]}",
            trust_score=trust_score,
        )
        content_hash = hashlib.sha256(
            f"{source}\0{session_id}\0{role}\0{text}".encode("utf-8")
        ).hexdigest()
        with closing(self.connect()) as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO episodic_entries
                        (source, session_id, role, content, content_hash, tags, trust_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (source, session_id, role, text, content_hash, tags, trust_score),
                )
                entry_id = int(cur.lastrowid)
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT entry_id FROM episodic_entries WHERE content_hash = ?",
                    (content_hash,),
                ).fetchone()
                entry_id = int(row["entry_id"])
            conn.commit()
        self._update_event_ref(event_id, "episodic_entries", entry_id)
        return entry_id

    def consolidate_session(
        self,
        *,
        source: str,
        session_id: str,
        max_semantic_facts: int = 3,
    ) -> int:
        entries = self.episodic_session(source=source, session_id=session_id)
        if not entries:
            return 0
        summary = _session_summary(source, session_id, entries)
        summary_id = self.add_fact(
            summary,
            category="general",
            tags=f"capture,{source},session-summary,session:{session_id}",
            trust_score=0.45,
            memory_type="resource",
            scope="global",
            key=f"session-summary:{source}:{session_id}",
            source="capture",
        )
        for entry in _semantic_candidates(entries)[:max_semantic_facts]:
            distilled = _distill_fact(str(entry["content"]))
            if not distilled:
                continue
            self.add_fact(
                f"[distilled {source} memory] {distilled}",
                category="general",
                tags=f"capture,{source},distilled,role:{entry['role']},session:{session_id}",
                trust_score=0.50,
                memory_type="semantic",
                scope="global",
                key=f"distilled:{source}:{session_id}:{_short_hash(str(entry['content']))}",
                source="capture",
            )
        return summary_id

    def episodic_session(self, *, source: str, session_id: str) -> list[sqlite3.Row]:
        self.ensure()
        with closing(self.connect()) as conn:
            return conn.execute(
                """
                SELECT entry_id, source, session_id, role, content, tags, trust_score, created_at
                FROM episodic_entries
                WHERE source = ? AND session_id = ?
                ORDER BY entry_id
                """,
                (source, session_id),
            ).fetchall()

    def prune_episodic(self, *, max_entries: int = 1000, max_age_days: int = 30) -> int:
        self.ensure()
        with closing(self.connect()) as conn:
            before = int(conn.execute("SELECT COUNT(*) FROM episodic_entries").fetchone()[0])
            conn.execute(
                """
                DELETE FROM episodic_entries
                WHERE created_at < datetime('now', ?)
                  AND retrieval_count = 0
                  AND trust_score < 0.50
                """,
                (f"-{max(1, int(max_age_days))} days",),
            )
            conn.execute(
                """
                DELETE FROM episodic_entries
                WHERE entry_id IN (
                    SELECT entry_id
                    FROM episodic_entries
                    ORDER BY retrieval_count ASC, trust_score ASC, created_at ASC
                    LIMIT max(0, (SELECT COUNT(*) FROM episodic_entries) - ?)
                )
                """,
                (max(1, int(max_entries)),),
            )
            after = int(conn.execute("SELECT COUNT(*) FROM episodic_entries").fetchone()[0])
            conn.commit()
        return before - after

    def list(
        self,
        limit: int = 25,
        include_superseded: bool = False,
        scope: MemoryScope = "project",
    ) -> list[Fact]:
        self.ensure()
        limit = _bounded_limit(limit, upper=100)
        clauses = []
        params: list[object] = []
        if not include_superseded:
            clauses.append("superseded_by IS NULL")
        clauses.append(f"scope IN ({','.join('?' for _ in _visible_scopes(scope))})")
        params.extend(_visible_scopes(scope))
        where = f"WHERE {' AND '.join(clauses)}"
        with closing(self.connect()) as conn:
            rows = conn.execute(
                f"""
                SELECT fact_id, content, category, tags, trust_score, memory_type, scope, key, version, source, provenance
                FROM facts
                {where}
                ORDER BY fact_id DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def search(self, query: str, limit: int = 10, scope: MemoryScope = "project") -> list[Fact]:
        self.ensure()
        query = query.strip()
        if not query:
            return []
        limit = _bounded_limit(limit, upper=25)
        scopes = _visible_scopes(scope)
        scope_filter = ",".join("?" for _ in scopes)
        with closing(self.connect()) as conn:
            rows: list[sqlite3.Row] = []
            try:
                rows.extend(conn.execute(
                    """
                    SELECT f.fact_id, f.content, f.category, f.tags, f.trust_score,
                           f.memory_type, f.scope, f.key, f.version, f.source, f.provenance,
                           f.updated_at
                    FROM facts f
                    JOIN facts_fts fts ON fts.rowid = f.fact_id
                    WHERE facts_fts MATCH ?
                      AND f.superseded_by IS NULL
                      AND f.memory_type != 'episodic'
                      AND f.scope IN ({scope_filter})
                    ORDER BY f.trust_score DESC, f.updated_at DESC, f.fact_id DESC
                    LIMIT ?
                    """.format(scope_filter=scope_filter),
                    (_fts_query(query), *scopes, limit),
                ).fetchall())
            except sqlite3.OperationalError:
                rows = []
            rows.extend(conn.execute(
                f"""
                    SELECT fact_id, content, category, tags, trust_score,
                           memory_type, scope, key, version, source, provenance,
                           updated_at
                    FROM facts
                    WHERE superseded_by IS NULL
                      AND memory_type != 'episodic'
                      AND scope IN ({scope_filter})
                      AND (
                        lower(content) LIKE lower(?)
                        OR lower(tags) LIKE lower(?)
                        OR lower(category) LIKE lower(?)
                        OR lower(key) LIKE lower(?)
                      )
                    ORDER BY trust_score DESC, updated_at DESC, fact_id DESC
                    LIMIT ?
                    """,
                (*scopes, f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall())
        return _dedupe_current([_row_to_fact(row) for row in rows])

    def current(self, key: str, scope: MemoryScope = "project") -> Fact | None:
        self.ensure()
        normalized = _normalize_key(key)
        if not normalized:
            return None
        scopes = _visible_scopes(scope)
        with closing(self.connect()) as conn:
            rows = conn.execute(
                f"""
                SELECT fact_id, content, category, tags, trust_score, memory_type, scope, key, version, source, provenance
                FROM facts
                WHERE key = ? AND superseded_by IS NULL
                  AND scope IN ({','.join('?' for _ in scopes)})
                """,
                (normalized, *scopes),
            ).fetchall()
        facts = [_row_to_fact(row) for row in rows]
        return max(facts, key=_fact_freshness_key) if facts else None

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

        with closing(self.connect()) as conn:
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

        self.consolidate()
        return True

    def remove(self, fact_id: int) -> bool:
        self.ensure()
        current = self._get_fact(fact_id)
        if current is None:
            return False
        with closing(self.connect()) as conn:
            conn.execute("DELETE FROM facts WHERE fact_id = ?", (fact_id,))
            conn.commit()
        self.consolidate()
        return True

    def write_handoff(
        self,
        *,
        scope: str = "global",
        goal: str,
        repo_state: str = "",
        files_touched: str = "",
        decisions: str = "",
        blockers: str = "",
        assumptions: str = "",
        validation: str = "",
        next_steps: str = "",
        evidence: str = "",
    ) -> int:
        self.ensure()
        with closing(self.connect()) as conn:
            cur = conn.execute(
                """
                INSERT INTO handoffs
                    (scope, goal, repo_state, files_touched, decisions, blockers,
                     assumptions, validation, next_steps, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scope,
                    _normalize_content(goal),
                    _normalize_content(repo_state),
                    _normalize_content(files_touched),
                    _normalize_content(decisions),
                    _normalize_content(blockers),
                    _normalize_content(assumptions),
                    _normalize_content(validation),
                    _normalize_content(next_steps),
                    _normalize_content(evidence),
                ),
            )
            handoff_id = int(cur.lastrowid)
            conn.commit()
        self.add_fact(
            f"Handoff goal: {goal}. Next: {next_steps or 'not specified'}",
            category="general",
            tags=f"handoff,scope:{scope}",
            trust_score=0.80,
            memory_type="handoff",
            scope="handoff",
            key=f"handoff:{scope}",
            source="handoff",
        )
        self.add_event(
            event_type="handoff.write",
            scope=scope,
            source="handoff",
            content=goal,
            ref_table="handoffs",
            ref_id=handoff_id,
            trust_score=0.80,
        )
        self.consolidate()
        return handoff_id

    def latest_handoff(self, scope: str = "global") -> Handoff | None:
        self.ensure()
        with closing(self.connect()) as conn:
            row = conn.execute(
                """
                SELECT handoff_id, scope, goal, repo_state, files_touched, decisions,
                       blockers, assumptions, validation, next_steps, evidence, created_at
                FROM handoffs
                WHERE scope = ?
                ORDER BY handoff_id DESC
                LIMIT 1
                """,
                (scope,),
            ).fetchone()
        return _row_to_handoff(row) if row else None

    def consolidate(self, *, user_limit: int = 12, memory_limit: int = 24) -> None:
        """Regenerate small USER.md and MEMORY.md working-set views."""

        self.ensure()
        user_facts = [
            fact
            for fact in self.list(limit=100)
            if fact.category == "user_pref"
        ][:user_limit]
        memory_facts = [
            fact
            for fact in self.list(limit=100)
            if fact.category != "user_pref"
            and fact.memory_type in {"semantic", "procedural", "resource", "handoff"}
        ][:memory_limit]
        self._write_generated_view(
            self.user_file,
            "Mneme Generated User Working Set",
            user_facts,
            self.latest_handoff("global"),
        )
        self._write_generated_view(
            self.memory_file,
            "Mneme Generated Project Working Set",
            memory_facts,
            self.latest_handoff("project"),
        )

    def _get_fact(self, fact_id: int) -> Fact | None:
        with closing(self.connect()) as conn:
            row = conn.execute(
                """
                SELECT fact_id, content, category, tags, trust_score, memory_type, scope, key, version, source, provenance
                FROM facts
                WHERE fact_id = ?
                """,
                (fact_id,),
            ).fetchone()
        return _row_to_fact(row) if row else None

    def _insert_fact(
        self,
        content: str,
        category: str,
        tags: str,
        trust_score: float = 0.65,
        memory_type: str = "semantic",
        scope: str = "global",
        key: str = "",
        version: str = "",
        source: str = "manual",
        provenance: str = "",
    ) -> int:
        with closing(self.connect()) as conn:
            supersedes_id = None
            superseded_by = None
            if key:
                rows = conn.execute(
                    """
                    SELECT fact_id, content, category, tags, trust_score, memory_type, scope, key, version, source, provenance
                    FROM facts
                    WHERE key = ? AND superseded_by IS NULL
                    """,
                    (key,),
                ).fetchall()
                facts = [_row_to_fact(row) for row in rows]
                current = max(facts, key=_fact_freshness_key) if facts else None
                if current is not None:
                    if (_parse_version(version), 10**18) >= _fact_freshness_key(current):
                        supersedes_id = current.fact_id
                    else:
                        superseded_by = current.fact_id
            try:
                cur = conn.execute(
                    """
                    INSERT INTO facts
                        (content, category, tags, trust_score, memory_type, scope,
                         key, version, supersedes_id, superseded_by, source, provenance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        content,
                        category,
                        tags,
                        max(0.0, min(1.0, float(trust_score))),
                        memory_type,
                        scope,
                        key,
                        version,
                        supersedes_id,
                        superseded_by,
                        source,
                        provenance,
                    ),
                )
                fact_id = int(cur.lastrowid)
                if supersedes_id is not None:
                    conn.execute(
                        "UPDATE facts SET superseded_by = ? WHERE fact_id = ?",
                        (fact_id, supersedes_id),
                    )
                conn.commit()
                return fact_id
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT fact_id FROM facts WHERE content = ?",
                    (content,),
                ).fetchone()
                return int(row["fact_id"])

    def _insert_event(
        self,
        *,
        event_type: str,
        scope: str = "global",
        source: str = "manual",
        content: str = "",
        ref_table: str = "",
        ref_id: int | None = None,
        trust_score: float = 0.5,
    ) -> int:
        with closing(self.connect()) as conn:
            cur = conn.execute(
                """
                INSERT INTO events (event_type, scope, source, content, ref_table, ref_id, trust_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    scope,
                    source,
                    _normalize_content(content),
                    ref_table,
                    ref_id,
                    max(0.0, min(1.0, float(trust_score))),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def _update_event_ref(self, event_id: int, ref_table: str, ref_id: int) -> None:
        with closing(self.connect()) as conn:
            conn.execute(
                "UPDATE events SET ref_table = ?, ref_id = ? WHERE event_id = ?",
                (ref_table, ref_id, event_id),
            )
            conn.commit()

    def _target_path(self, target: MemoryTarget) -> Path:
        return self.user_file if target == "user" else self.memory_file

    def _write_generated_view(
        self,
        path: Path,
        title: str,
        facts: list[Fact],
        handoff: Handoff | None,
    ) -> None:
        lines = [
            GENERATED_HEADER,
            f"# {title}",
            "",
            "This file is generated by `mneme-memory consolidate`; retrieve older details with `mneme-memory search`.",
            "",
        ]
        if facts:
            lines.extend(f"- {fact.content}" for fact in facts)
        else:
            lines.append("- No current facts.")
        if handoff is not None:
            lines.extend(
                [
                    "",
                    "## Latest Handoff",
                    f"- Goal: {handoff.goal}",
                    f"- Next: {handoff.next_steps or 'not specified'}",
                    f"- Validation: {handoff.validation or 'not specified'}",
                ]
            )
        lines.extend(["", GENERATED_FOOTER, ""])
        path.write_text("\n".join(lines), encoding="utf-8")


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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    memory_type TEXT DEFAULT 'semantic',
    scope TEXT DEFAULT 'global',
    key TEXT DEFAULT '',
    version TEXT DEFAULT '',
    supersedes_id INTEGER,
    superseded_by INTEGER,
    source TEXT DEFAULT 'manual',
    provenance TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    scope TEXT DEFAULT 'global',
    source TEXT DEFAULT 'manual',
    content TEXT DEFAULT '',
    ref_table TEXT DEFAULT '',
    ref_id INTEGER,
    trust_score REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS episodic_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    session_id TEXT DEFAULT '',
    role TEXT DEFAULT '',
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    tags TEXT DEFAULT '',
    trust_score REAL DEFAULT 0.3,
    retrieval_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS handoffs (
    handoff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT DEFAULT 'global',
    goal TEXT NOT NULL,
    repo_state TEXT DEFAULT '',
    files_touched TEXT DEFAULT '',
    decisions TEXT DEFAULT '',
    blockers TEXT DEFAULT '',
    assumptions TEXT DEFAULT '',
    validation TEXT DEFAULT '',
    next_steps TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
    USING fts5(content, tags, content=facts, content_rowid=fact_id);
"""


TRIGGERS = """
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


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TRIGGER IF EXISTS facts_ai;
        DROP TRIGGER IF EXISTS facts_ad;
        DROP TRIGGER IF EXISTS facts_au;
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
    additions = {
        "memory_type": "TEXT DEFAULT 'semantic'",
        "scope": "TEXT DEFAULT 'global'",
        "key": "TEXT DEFAULT ''",
        "version": "TEXT DEFAULT ''",
        "supersedes_id": "INTEGER",
        "superseded_by": "INTEGER",
        "source": "TEXT DEFAULT 'manual'",
        "provenance": "TEXT DEFAULT ''",
    }
    for name, ddl in additions.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE facts ADD COLUMN {name} {ddl}")
    _quarantine_legacy_conversations(conn)
    conn.execute(
        """
        UPDATE facts
        SET memory_type = CASE
                WHEN category = 'tool' THEN 'procedural'
                WHEN category = 'project' THEN 'semantic'
                ELSE 'semantic'
            END,
            scope = CASE WHEN category = 'project' THEN 'project' ELSE 'global' END
        WHERE memory_type IS NULL OR memory_type = ''
        """
    )
    _rebuild_fts(conn)
    conn.executescript(TRIGGERS)


def _row_to_fact(row: sqlite3.Row) -> Fact:
    return Fact(
        fact_id=int(row["fact_id"]),
        content=str(row["content"]),
        category=str(row["category"]),
        tags=str(row["tags"] or ""),
        trust_score=float(row["trust_score"]),
        memory_type=str(row["memory_type"] or "semantic"),
        scope=str(row["scope"] or "global"),
        key=str(row["key"] or ""),
        version=str(row["version"] or ""),
        source=str(row["source"] or "manual") if "source" in row.keys() else "manual",
        provenance=str(row["provenance"] or "") if "provenance" in row.keys() else "",
    )


def _row_to_handoff(row: sqlite3.Row) -> Handoff:
    return Handoff(
        handoff_id=int(row["handoff_id"]),
        scope=str(row["scope"] or "global"),
        goal=str(row["goal"] or ""),
        repo_state=str(row["repo_state"] or ""),
        files_touched=str(row["files_touched"] or ""),
        decisions=str(row["decisions"] or ""),
        blockers=str(row["blockers"] or ""),
        assumptions=str(row["assumptions"] or ""),
        validation=str(row["validation"] or ""),
        next_steps=str(row["next_steps"] or ""),
        evidence=str(row["evidence"] or ""),
        created_at=str(row["created_at"] or ""),
    )


def _normalize_content(content: str | None) -> str:
    return re.sub(r"\s+", " ", (content or "").strip())


def _normalize_key(key: str | None) -> str:
    return re.sub(r"[^a-z0-9_.:/-]+", "-", (key or "").strip().lower()).strip("-")


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


def _dedupe_current(facts: list[Fact]) -> list[Fact]:
    seen: set[str] = set()
    kept: list[Fact] = []
    for fact in sorted(facts, key=_fact_rank_key, reverse=True):
        marker = fact.key or f"content:{fact.content}"
        if marker in seen:
            continue
        seen.add(marker)
        kept.append(fact)
    return kept


def _visible_scopes(scope: str) -> tuple[str, ...]:
    if scope == "global":
        return ("global",)
    if scope == "project":
        return ("global", "project")
    if scope == "handoff":
        return ("handoff",)
    if scope == "agent-private":
        return ("agent-private",)
    return ("global", "project")


def _fact_rank_key(fact: Fact) -> tuple[float, tuple[int, ...], int]:
    return (fact.trust_score, _parse_version(fact.version), fact.fact_id)


def _fact_freshness_key(fact: Fact) -> tuple[tuple[int, ...], int]:
    return (_parse_version(fact.version), fact.fact_id)


def _parse_version(version: str) -> tuple[int, ...]:
    text = (version or "").strip().lower()
    if not text:
        return (0,)
    if text in {"now", "current", "latest"}:
        return (9999, 12, 31, 23, 59, 59)
    parts = [int(part) for part in re.findall(r"\d+", text)]
    if not parts:
        return (0,)
    return tuple(parts)


def _quarantine_legacy_conversations(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT fact_id, content, tags, trust_score, created_at
        FROM facts
        WHERE category = 'conversation'
        """
    ).fetchall()
    for row in rows:
        content = _normalize_content(str(row["content"]))
        if not content:
            conn.execute("DELETE FROM facts WHERE fact_id = ?", (row["fact_id"],))
            continue
        tags = str(row["tags"] or "legacy,conversation")
        source = _tag_value(tags, "source") or ("codex" if "codex" in tags else "claude" if "claude" in tags else "legacy")
        session_id = _tag_value(tags, "session") or f"legacy-fact-{row['fact_id']}"
        role = _tag_value(tags, "role") or "unknown"
        content_hash = hashlib.sha256(
            f"legacy\0{row['fact_id']}\0{content}".encode("utf-8")
        ).hexdigest()
        conn.execute(
            """
            INSERT OR IGNORE INTO episodic_entries
                (source, session_id, role, content, content_hash, tags, trust_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                session_id,
                role,
                content,
                content_hash,
                tags,
                max(0.0, min(1.0, float(row["trust_score"] or 0.30))),
                row["created_at"],
            ),
        )
        entry = conn.execute(
            "SELECT entry_id FROM episodic_entries WHERE content_hash = ?",
            (content_hash,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO events (event_type, scope, source, content, ref_table, ref_id, trust_score, created_at)
            SELECT ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM events
                WHERE event_type = ? AND ref_table = ? AND ref_id = ?
            )
            """,
            (
                "migration.quarantine_conversation",
                "global",
                "migration",
                content[:240],
                "episodic_entries",
                int(entry["entry_id"]) if entry else None,
                max(0.0, min(1.0, float(row["trust_score"] or 0.30))),
                row["created_at"],
                "migration.quarantine_conversation",
                "episodic_entries",
                int(entry["entry_id"]) if entry else None,
            ),
        )
        conn.execute("DELETE FROM facts WHERE fact_id = ?", (row["fact_id"],))


def _tag_value(tags: str, name: str) -> str:
    match = re.search(rf"(?:^|,){re.escape(name)}:([^,]+)", tags)
    return match.group(1).strip() if match else ""


def _rebuild_fts(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")
    except sqlite3.OperationalError:
        pass


def _session_summary(source: str, session_id: str, entries: list[sqlite3.Row]) -> str:
    roles = sorted({str(row["role"] or "unknown") for row in entries})
    return (
        f"[{source} session summary] session={session_id}: "
        f"{len(entries)} archived turns; roles={','.join(roles)}. Raw turns are in episodic archive."
    )


def _semantic_candidates(entries: list[sqlite3.Row]) -> list[sqlite3.Row]:
    needles = (
        "remember",
        "prefers",
        "decided",
        "root cause",
        "fix",
        "bug",
        "todo",
        "next",
        "commit",
        "installed",
        "configured",
        "default",
        "must",
        "do not",
        "standing rule",
    )
    return [row for row in entries if any(needle in str(row["content"]).lower() for needle in needles)]


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _distill_fact(text: str) -> str:
    text = _normalize_content(text)
    text = re.sub(r"(?i)^(please\s+)?remember\s+(that\s+)?", "", text)
    text = re.sub(r"(?i)^(note\s+that|important:)\s*", "", text)
    return _truncate(text, 420)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 16)].rstrip() + " ... [truncated]"


# TODO(mneme): add optional embedding and temporal/entity graph indexes beside FTS5.
# Keep FTS as the default exact-symbol path; merge/dedupe semantic/graph hits here.
