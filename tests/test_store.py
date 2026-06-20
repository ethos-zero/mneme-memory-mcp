from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from caduceus_memory_mcp.store import SharedMemoryStore


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

