from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from sqlite3 import connect

from mneme_memory_mcp.store import SharedMemoryStore


class SharedMemoryStoreTest(unittest.TestCase):
    def make_store(self) -> SharedMemoryStore:
        root = Path(tempfile.mkdtemp())
        return SharedMemoryStore(home=root)

    def test_add_summary_search_list(self) -> None:
        store = self.make_store()

        first = store.add(
            "Zach prefers concise but warm responses.",
            target="user",
            category="user_pref",
            tags="style",
        )
        second = store.add(
            "Voicebox uses the Codex Sky profile.",
            target="memory",
            category="tool",
            tags="voicebox,codex",
        )

        self.assertEqual(first, 1)
        self.assertEqual(second, 2)
        self.assertIn("Zach prefers", store.summary())
        self.assertIn("Voicebox uses", store.summary())
        self.assertEqual(store.search("Voicebox")[0].fact_id, 2)
        self.assertEqual(len(store.list()), 2)

    def test_duplicate_content_returns_existing_id(self) -> None:
        store = self.make_store()
        first = store.add("Same fact.", target="memory")
        second = store.add("Same fact.", target="memory")

        self.assertEqual(first, second)
        self.assertEqual(len(store.list()), 1)

    def test_add_fact_can_skip_markdown(self) -> None:
        store = self.make_store()

        fact_id = store.add_fact(
            "Captured tool note about Buffer posting.",
            category="tool",
            tags="capture,claude",
            append_markdown=False,
            trust_score=0.35,
        )

        self.assertEqual(fact_id, 1)
        self.assertIn("Buffer posting", store.search("Buffer")[0].content)
        self.assertEqual(store.search("Buffer")[0].trust_score, 0.35)
        self.assertNotIn("Captured tool note", store.summary())

    def test_episodic_capture_distills_summary_not_raw_fact(self) -> None:
        store = self.make_store()

        store.add_episodic(
            source="codex",
            session_id="session-1",
            role="user",
            text="Please remember that the test command is python -m unittest.",
            tags="capture,codex",
        )
        store.consolidate_session(source="codex", session_id="session-1")

        self.assertEqual(store.search("archived turns")[0].memory_type, "resource")
        self.assertIn("test command", store.search("test command")[0].content)

    def test_supersession_resolves_current_key(self) -> None:
        store = self.make_store()

        old_id = store.add("Test command is pnpm test.", key="test-command", version="1")
        new_id = store.add("Test command is bun test.", key="test-command", version="2")

        current = store.current("test-command")
        self.assertIsNotNone(current)
        self.assertEqual(current.fact_id, new_id)
        self.assertNotIn(old_id, [fact.fact_id for fact in store.search("test command", limit=10)])

    def test_supersession_uses_version_parser_not_arrival_order(self) -> None:
        store = self.make_store()

        new_id = store.add("Test command is bun test.", key="test-command", version="10")
        old_id = store.add("Test command is pnpm test.", key="test-command", version="2")

        current = store.current("test-command")
        self.assertIsNotNone(current)
        self.assertEqual(current.fact_id, new_id)
        self.assertNotIn(old_id, [fact.fact_id for fact in store.search("test command", limit=10)])

    def test_scope_visibility_gates_search(self) -> None:
        store = self.make_store()

        store.add_fact("Global fact is visible.", scope="global")
        store.add_fact("Project fact is visible.", scope="project")
        store.add_fact("Private scratch must stay hidden.", scope="agent-private")
        store.add_fact("Handoff note is separate.", memory_type="handoff", scope="handoff")

        self.assertEqual(store.search("Private scratch"), [])
        self.assertIn("Private scratch", store.search("Private scratch", scope="agent-private")[0].content)
        self.assertEqual(store.search("Handoff note"), [])
        self.assertIn("Handoff note", store.search("Handoff note", scope="handoff")[0].content)
        self.assertIn("Global fact", store.search("Global fact", scope="project")[0].content)
        self.assertIn("Project fact", store.search("Project fact", scope="project")[0].content)

    def test_episodic_cap_prunes_old_low_trust_entries(self) -> None:
        store = self.make_store()
        for index in range(5):
            store.add_episodic(
                source="codex",
                session_id=f"s{index}",
                role="user",
                text=f"raw archived turn {index}",
            )

        pruned = store.prune_episodic(max_entries=2, max_age_days=999)

        self.assertEqual(pruned, 3)
        with store.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM episodic_entries").fetchone()[0]
        self.assertEqual(count, 2)

    def test_migrates_v060_conversations_to_episodic_not_facts_idempotently(self) -> None:
        root = Path(tempfile.mkdtemp())
        db_path = root / "memory_store.db"
        with connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE facts (
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
                INSERT INTO facts (content, category, tags, trust_score)
                VALUES
                    ('[codex conversation capture] raw secret transcript about deploy', 'conversation', 'capture,codex,session:abc,role:user', 0.30),
                    ('Zach prefers concise replies.', 'user_pref', 'style', 0.90),
                    ('Mneme repo uses unittest.', 'project', 'tests', 0.80);
                """
            )

        store = SharedMemoryStore(home=root, db_path=db_path)
        store.ensure()
        store.ensure()

        with store.connect() as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
            episodic = conn.execute("SELECT content, source, session_id, role FROM episodic_entries").fetchall()
            conversation_facts = conn.execute("SELECT COUNT(*) FROM facts WHERE category = 'conversation'").fetchone()[0]
            events = conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'migration.quarantine_conversation'").fetchone()[0]

        self.assertTrue({"memory_type", "scope", "key", "version", "supersedes_id", "superseded_by", "source", "provenance"} <= columns)
        self.assertEqual(conversation_facts, 0)
        self.assertEqual(len(episodic), 1)
        self.assertIn("raw secret transcript", episodic[0]["content"])
        self.assertEqual(episodic[0]["source"], "codex")
        self.assertEqual(episodic[0]["session_id"], "abc")
        self.assertEqual(episodic[0]["role"], "user")
        self.assertEqual(events, 1)
        self.assertEqual(store.search("raw secret transcript"), [])
        self.assertIn("concise replies", store.search("concise")[0].content)
        self.assertIn("unittest", store.search("unittest")[0].content)

    def test_handoff_round_trip(self) -> None:
        store = self.make_store()

        handoff_id = store.write_handoff(
            scope="project",
            goal="Finish memory overhaul.",
            files_touched="src/mneme_memory_mcp/store.py",
            validation="tests pending",
            next_steps="run unittest",
        )
        handoff = store.latest_handoff("project")

        self.assertEqual(handoff_id, 1)
        self.assertIsNotNone(handoff)
        self.assertIn("Finish memory overhaul", handoff.format())
        self.assertIn("run unittest", store.summary())

    def test_update_and_remove(self) -> None:
        store = self.make_store()
        fact_id = store.add("Old fact.", target="memory")

        self.assertTrue(store.update(fact_id, content="New fact.", tags="updated"))
        self.assertIn("New fact.", store.summary())
        self.assertNotIn("Old fact.", store.summary())

        self.assertTrue(store.remove(fact_id))
        self.assertEqual(store.search("New fact"), [])
        self.assertNotIn("New fact.", store.summary())


if __name__ == "__main__":
    unittest.main()
