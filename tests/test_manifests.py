"""The plugin manifests stay in step with the Python package.

One version for the whole repository: the PyPI package, the Claude Code
plugin and the Gemini CLI extension. Bump them together; the publish
workflow runs this test before it uploads anything.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCP_URL = "https://api.pdata.world/mcp"


def _load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


@unittest.skipUnless(
    (ROOT / ".claude-plugin" / "plugin.json").exists(), "plugin files are not in this copy"
)
class ManifestTests(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "src" / "pdata" / "_version.py").read_text(encoding="utf-8")
        self.version = re.search(r'__version__ = "([^"]+)"', text).group(1)

    def test_versions_match_the_package(self):
        self.assertEqual(_load(".claude-plugin/plugin.json")["version"], self.version)
        self.assertEqual(_load("gemini-extension.json")["version"], self.version)

    def test_every_manifest_points_at_the_hosted_server(self):
        claude = _load(".mcp.json")["mcpServers"]["pdata"]
        gemini = _load("gemini-extension.json")["mcpServers"]["pdata"]
        self.assertEqual((claude["type"], claude["url"]), ("http", MCP_URL))
        self.assertEqual((gemini["type"], gemini["url"]), ("http", MCP_URL))

    def test_names_line_up(self):
        plugin = _load(".claude-plugin/plugin.json")["name"]
        entry = _load(".claude-plugin/marketplace.json")["plugins"][0]
        self.assertEqual(entry["name"], plugin)
        self.assertEqual(entry["source"], "./")
        self.assertEqual(_load("gemini-extension.json")["name"], plugin)
        skill = (ROOT / "skills" / "pdata-prediction-markets" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(skill.startswith("---\nname: pdata-prediction-markets\n"))


if __name__ == "__main__":
    unittest.main()
