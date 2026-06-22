from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from mneme_memory_mcp.continuity import (
    MANAGED_START,
    ContinuityPaths,
    continuity_status,
    install_continuity,
)


class ContinuityTest(unittest.TestCase):
    def make_paths(self, root: Path) -> ContinuityPaths:
        home = root / "home"
        return ContinuityPaths(
            memory_home=root / "memory",
            bin_dir=root / "repo" / ".venv" / "bin",
            codex_agents=home / ".codex" / "AGENTS.md",
            codex_config=home / ".codex" / "config.toml",
            codex_notify_wrapper=home / ".codex" / "mneme-memory-notify.sh",
            claude_md=home / ".claude" / "CLAUDE.md",
            claude_settings=home / ".claude" / "settings.json",
            claude_hook=home / ".claude" / "hooks" / "mneme-memory-sessionstart.sh",
            claude_capture_hook=home / ".claude" / "hooks" / "mneme-memory-capture.sh",
        )

    def test_install_continuity_preserves_existing_files_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.make_paths(root)
            paths.codex_agents.parent.mkdir(parents=True)
            paths.claude_md.parent.mkdir(parents=True)
            paths.codex_agents.write_text("# Existing Codex Notes\n", encoding="utf-8")
            paths.claude_md.write_text("# Existing Claude Notes\n", encoding="utf-8")
            paths.claude_settings.write_text(
                json.dumps({"enabledPlugins": {"codex@openai-codex": True}}),
                encoding="utf-8",
            )
            paths.codex_config.parent.mkdir(parents=True, exist_ok=True)
            paths.codex_config.write_text(
                'notify = ["/usr/local/bin/existing-notify", "turn-ended"]\n',
                encoding="utf-8",
            )

            first = install_continuity(paths)
            second = install_continuity(paths)

            codex_text = paths.codex_agents.read_text(encoding="utf-8")
            claude_text = paths.claude_md.read_text(encoding="utf-8")
            settings = json.loads(paths.claude_settings.read_text(encoding="utf-8"))
            codex_config = paths.codex_config.read_text(encoding="utf-8")
            hook_executable = os.access(paths.claude_hook, os.X_OK)
            capture_hook_executable = os.access(paths.claude_capture_hook, os.X_OK)
            notify_executable = os.access(paths.codex_notify_wrapper, os.X_OK)

        self.assertTrue(first.codex_instructions)
        self.assertTrue(second.claude_sessionstart_hook)
        self.assertTrue(second.claude_stop_capture_hook)
        self.assertTrue(second.claude_sessionend_capture_hook)
        self.assertTrue(second.codex_notify_capture)
        self.assertIn("# Existing Codex Notes", codex_text)
        self.assertIn("# Existing Claude Notes", claude_text)
        self.assertEqual(codex_text.count(MANAGED_START), 1)
        self.assertEqual(claude_text.count(MANAGED_START), 1)
        self.assertTrue(hook_executable)
        self.assertTrue(capture_hook_executable)
        self.assertTrue(notify_executable)
        self.assertEqual(settings["enabledPlugins"]["codex@openai-codex"], True)
        self.assertIn("SessionStart", settings["hooks"])
        self.assertIn("Stop", settings["hooks"])
        self.assertIn("SessionEnd", settings["hooks"])
        self.assertEqual(settings["hooks"]["Stop"][0]["hooks"][0]["command"], str(paths.claude_capture_hook))
        self.assertIn(str(paths.codex_notify_wrapper), codex_config)
        self.assertIn("turn-ended", codex_config)
        self.assertEqual(codex_config.count("notify ="), 1)

    def test_existing_hermes_session_hook_counts_as_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.make_paths(root)
            paths.claude_settings.parent.mkdir(parents=True)
            paths.claude_settings.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "/Users/me/.claude/hooks/hermes-memory.sh",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            install_continuity(paths)
            status = continuity_status(paths)
            settings_text = paths.claude_settings.read_text(encoding="utf-8")

        self.assertTrue(status.claude_sessionstart_hook)
        self.assertTrue(status.claude_stop_capture_hook)
        self.assertIn("hermes-memory.sh", settings_text)
        self.assertNotIn("mneme-memory-sessionstart.sh", settings_text)
        self.assertIn("mneme-memory-capture.sh", settings_text)


if __name__ == "__main__":
    unittest.main()
