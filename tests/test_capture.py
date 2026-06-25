from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mneme_memory_mcp.capture import _capture_source, parse_claude_jsonl, parse_codex_jsonl
from mneme_memory_mcp.store import SharedMemoryStore


class CaptureTest(unittest.TestCase):
    def write_jsonl(self, records: list[dict]) -> Path:
        root = Path(tempfile.mkdtemp())
        path = root / "session.jsonl"
        path.write_text(
            "\n".join(json.dumps(record) for record in records) + "\n",
            encoding="utf-8",
        )
        return path

    def test_parse_claude_queue_and_tool_result(self) -> None:
        path = self.write_jsonl(
            [
                {
                    "type": "queue-operation",
                    "operation": "enqueue",
                    "sessionId": "claude-1",
                    "content": "Please post the quote card to Buffer.",
                },
                {
                    "type": "message",
                    "sessionId": "claude-1",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "content": "Pinterest result: PostActionSuccess id 123",
                            }
                        ],
                    },
                },
            ]
        )

        snippets = parse_claude_jsonl(path)

        self.assertEqual(len(snippets), 2)
        self.assertEqual(snippets[0].source, "claude")
        self.assertIn("Buffer", snippets[0].text)
        self.assertIn("PostActionSuccess", snippets[1].text)

    def test_parse_codex_messages_and_redacts_secret(self) -> None:
        path = self.write_jsonl(
            [
                {
                    "type": "session_meta",
                    "payload": {"id": "codex-1", "base_instructions": {"text": "skip me"}},
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "Use token=abc123 to inspect Buffer work.",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "I found the Buffer post draft."}],
                    },
                },
            ]
        )

        snippets = parse_codex_jsonl(path)

        self.assertEqual(len(snippets), 2)
        self.assertEqual(snippets[0].session_id, "codex-1")
        self.assertIn("token=[redacted]", snippets[0].text)
        self.assertIn("Buffer post draft", snippets[1].text)

    def test_capture_routes_raw_turns_to_episodic_and_distills_searchable_summary(self) -> None:
        path = self.write_jsonl(
            [
                {"type": "session_meta", "payload": {"id": "codex-1"}},
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "Please remember the deploy command is ./scripts/deploy.sh.",
                    },
                },
            ]
        )
        store = SharedMemoryStore(home=Path(tempfile.mkdtemp()))

        stats = _capture_source(
            source="codex",
            files=[path],
            parser=parse_codex_jsonl,
            store=store,
        )

        self.assertEqual(stats.snippets_indexed, 1)
        self.assertEqual(store.search("Please remember the deploy command"), [])
        self.assertIn("deploy command", store.search("deploy command")[0].content)
        with store.connect() as conn:
            episodic_count = conn.execute("SELECT COUNT(*) FROM episodic_entries").fetchone()[0]
            conversation_facts = conn.execute("SELECT COUNT(*) FROM facts WHERE category = 'conversation'").fetchone()[0]
            summaries = conn.execute("SELECT COUNT(*) FROM facts WHERE memory_type = 'resource'").fetchone()[0]
        self.assertEqual(episodic_count, 1)
        self.assertEqual(conversation_facts, 0)
        self.assertEqual(summaries, 1)


if __name__ == "__main__":
    unittest.main()
