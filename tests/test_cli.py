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


if __name__ == "__main__":
    unittest.main()
