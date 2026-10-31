"""Structural checks for the shared agent memory and handoff files."""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MEMORY_FILES = (
    "AGENTS.md",
    ".agents/memory/context.md",
    ".agents/memory/handoff.md",
    "docs/adr/README.md",
    "docs/agent-memory.md",
)

HANDOFF_FIELDS = (
    "Updated",
    "Agent",
    "Status",
    "Goal",
    "Done",
    "Next",
    "Blocked",
    "Verification",
)


class TestAgentMemory(unittest.TestCase):
    """Keep the shared memory small, linked, and free of duplicate rules."""

    def read(self, relative_path: str) -> str:
        path = os.path.join(ROOT, relative_path)
        self.assertTrue(
            os.path.isfile(path),
            f"missing shared memory file: {relative_path}",
        )
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_shared_files_exist(self):
        for relative_path in MEMORY_FILES:
            with self.subTest(file=relative_path):
                self.read(relative_path)

    def test_agents_file_fits_antigravity_rule_limit(self):
        text = self.read("AGENTS.md")
        self.assertIn("## Memory protocol", text)
        self.assertIn("## Handoff format", text)
        self.assertLessEqual(
            len(text.encode("utf-8")),
            24000,
            "AGENTS.md exceeds Antigravity's 24,000-byte rule limit",
        )

    def test_handoff_has_required_fields(self):
        text = self.read(".agents/memory/handoff.md")
        for field in HANDOFF_FIELDS:
            with self.subTest(field=field):
                self.assertTrue(
                    f"**{field}**" in text or f"## {field}" in text,
                    f"handoff is missing required field: {field}",
                )
        self.assertRegex(
            text,
            r"\*\*Status\*\*: (in-progress|blocked|ready-for-review|done)",
        )

    def test_memory_links_resolve(self):
        text = self.read("AGENTS.md")
        pattern = r"`((?:\.agents/memory/|docs/adr/)[^`]+|SKILL\.md)`"
        for relative_path in re.findall(pattern, text):
            with self.subTest(link=relative_path):
                self.assertTrue(
                    os.path.exists(os.path.join(ROOT, relative_path)),
                    f"broken memory link: {relative_path}",
                )

    def test_adr_index_links_resolve(self):
        text = self.read("docs/adr/README.md")
        for relative_path in re.findall(r"\]\((?!https?://)([^)]+\.md)\)", text):
            with self.subTest(link=relative_path):
                self.assertTrue(
                    os.path.exists(os.path.join(ROOT, "docs", "adr", relative_path)),
                    f"broken ADR index link: {relative_path}",
                )

    def test_no_duplicate_rule_source(self):
        rules_dir = os.path.join(ROOT, ".agents", "rules")
        if os.path.isdir(rules_dir):
            entries = [
                name for name in os.listdir(rules_dir) if name.endswith(".md")
            ]
            self.assertEqual(
                entries,
                [],
                ".agents/rules/*.md would duplicate AGENTS.md; keep shared rules "
                "in AGENTS.md",
            )


if __name__ == "__main__":
    unittest.main()
