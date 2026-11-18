"""Tests for OpenCode provider/model/MCP management."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import opencode_manage as oc

BASE = '''{
 // important comment
 "theme": "dark",
 "provider": {"local": {"models": {"test": {"name": "Test"}}}},
 "mcp": {"foo": {"type": "remote", "url": "https://example.org/mcp"}},
}
'''


class OpenCodeConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "opencode.jsonc"
        self.path.write_text(BASE, encoding="utf-8")
        patcher = patch.dict(os.environ, {"OMO_OPENCODE_CONFIG": str(self.path)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_preserves_other_sections_and_comments(self):
        oc.mutate("mcp", "foo", operation="toggle")
        source, data = oc.load()
        self.assertIn("// important comment", source)
        self.assertEqual(data["theme"], "dark")
        self.assertFalse(data["mcp"]["foo"]["enabled"])
        self.assertTrue(list(self.path.parent.glob("*.bak-*")))

    def test_add_edit_delete_custom_model(self):
        oc.provider_model("local", "new", {"name": "New"})
        self.assertIn("new", oc.load()[1]["provider"]["local"]["models"])
        oc.provider_model("local", "new", {"name": "New v2"})
        self.assertEqual(oc.load()[1]["provider"]["local"]["models"]["new"]["name"], "New v2")
        oc.provider_model("local", "new", operation="delete")
        self.assertNotIn("new", oc.load()[1]["provider"]["local"]["models"])

    def test_default_model(self):
        oc.save_section("model", "local/test", yes=True)
        self.assertEqual(oc.load()[1]["model"], "local/test")

    def test_add_local_and_remote_mcp(self):
        oc.mutate("mcp", "bar", {"type": "local", "command": ["npx", "-y", "foo"]})
        self.assertEqual(oc.load()[1]["mcp"]["bar"]["command"][0], "npx")
        oc.mutate("mcp", "remote", {"type": "remote", "url": "https://example.com/mcp"})
        self.assertEqual(oc.load()[1]["mcp"]["remote"]["type"], "remote")

    def test_delete_and_toggle_missing_raise(self):
        with self.assertRaises(ValueError):
            oc.mutate("mcp", "missing", operation="delete")
        with self.assertRaises(ValueError):
            oc.mutate("provider", "local", operation="toggle")

    def test_requires_explicit_confirmation(self):
        with self.assertRaises(ValueError):
            oc.save_section("model", "local/test")

    def test_jsonc_without_section_is_added(self):
        path = Path(self.temp.name) / "minimal.jsonc"
        path.write_text('{"theme":"dark"}\n', encoding="utf-8")
        with patch.dict(os.environ, {"OMO_OPENCODE_CONFIG": str(path)}):
            oc.save_section("model", "local/test", yes=True)
            self.assertEqual(json.loads(path.read_text())["model"], "local/test")
            self.assertEqual(json.loads(path.read_text())["theme"], "dark")

    def test_symlink_target_is_preserved(self):
        real = Path(self.temp.name) / "target.jsonc"
        real.write_text(BASE, encoding="utf-8")
        link = Path(self.temp.name) / "link.jsonc"
        link.symlink_to(real)
        with patch.dict(os.environ, {"OMO_OPENCODE_CONFIG": str(link)}):
            oc.mutate("mcp", "foo", operation="toggle")
        self.assertTrue(link.is_symlink())
        self.assertFalse(oc.parse(real.read_text())["mcp"]["foo"]["enabled"])

    def test_config_dir_precedence(self):
        with patch.dict(os.environ, {"OMO_OPENCODE_CONFIG": "", "OPENCODE_CONFIG_DIR": self.temp.name}):
            self.assertEqual(oc.config_path(), self.path)


if __name__ == "__main__":
    unittest.main()
