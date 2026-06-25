from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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
            "Captured transcript snippet about Buffer posting.",
            category="conversation",
            tags="capture,claude",
            append_markdown=False,
            trust_score=0.35,
        )

        self.assertEqual(fact_id, 1)
        self.assertIn("Buffer posting", store.search("Buffer")[0].content)
        self.assertEqual(store.search("Buffer")[0].trust_score, 0.35)
        self.assertNotIn("Captured transcript snippet", store.summary())

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
