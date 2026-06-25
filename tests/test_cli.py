from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mneme_memory_mcp.cli import main


class CliTest(unittest.TestCase):
    def run_cli(self, argv: list[str], memory_home: Path) -> str:
        output = io.StringIO()
        with patch.dict("os.environ", {"MNEME_HOME": str(memory_home)}, clear=False):
            with contextlib.redirect_stdout(output):
                main(argv)
        return output.getvalue()

    def test_add_summary_and_search_use_same_memory_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory_home = Path(tmp) / "memory"

            add_result = self.run_cli(
                ["add", "--target", "memory", "--tags", "test", "Codex and Claude share Mneme."],
                memory_home,
            )
            summary = self.run_cli(["summary"], memory_home)
            search = self.run_cli(["search", "Claude"], memory_home)

        self.assertIn("saved fact 1", add_result)
        self.assertIn("Codex and Claude share Mneme.", summary)
        self.assertIn("Codex and Claude share Mneme.", search)

    def test_current_and_handoff_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory_home = Path(tmp) / "memory"

            self.run_cli(
                ["add", "--key", "test-command", "--version", "1", "Test command is pnpm test."],
                memory_home,
            )
            self.run_cli(
                ["add", "--key", "test-command", "--version", "2", "Test command is bun test."],
                memory_home,
            )
            current = self.run_cli(["current", "test-command"], memory_home)
            write = self.run_cli(
                [
                    "handoff",
                    "write",
                    "--scope",
                    "project",
                    "--goal",
                    "Finish memory overhaul",
                    "--next-steps",
                    "run checks",
                ],
                memory_home,
            )
            latest = self.run_cli(["handoff", "latest", "--scope", "project"], memory_home)

        self.assertIn("bun test", current)
        self.assertNotIn("pnpm test", current)
        self.assertIn("saved handoff 1", write)
        self.assertIn("Finish memory overhaul", latest)


if __name__ == "__main__":
    unittest.main()
