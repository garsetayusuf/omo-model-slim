"""Tests for Slim configuration discovery, schema handling and safe writes."""

import json
import os
import stat
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import omo_model_slim as slim

ROOT = Path(__file__).resolve().parents[1]

SAMPLE = '''{
  // keep this comment
  "preset": "openai",
  "agents": {"oracle": {"model": "root/oracle", "variant": "low"}},
  "presets": {
    "base": {
      "orchestrator": {"model": ["base/primary", "base/fallback"], "variant": "medium", "skills": ["*"]},
      "explorer": {"model": "base/explorer"}
    },
    "openai": {
      "extends": "base",
      "orchestrator": {"model": "openai/primary"},
      "oracle": {
        "model": [{"id": "openai/oracle", "variant": "high"}, {"id": "openai/oracle-fb"}],
        "skills": ["simplify"]
      }
    }
  },
  "other": true,
}
'''


@contextmanager
def temp_config(content: str = SAMPLE, name: str = "oh-my-opencode-slim.jsonc"):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / name
        path.write_text(content, encoding="utf-8")
        with patch.object(slim, "CONFIG", path):
            yield path


class ParsingTests(unittest.TestCase):
    def test_jsonc_comments_trailing_commas_and_spans(self):
        data = slim.parse(SAMPLE)
        self.assertTrue(data["other"])
        spans = slim.token_spans(SAMPLE)
        self.assertEqual(json.loads(SAMPLE[spans[("presets", "openai", "orchestrator", "model")][0]:spans[("presets", "openai", "orchestrator", "model")][1]]), "openai/primary")

    def test_invalid_jsonc_reports_context_without_writing(self):
        with temp_config('{ "preset": "openai", "agents": { ') as path:
            original = path.read_text()
            with self.assertRaises(ValueError) as raised:
                slim.read()
            self.assertIn("Invalid JSONC", str(raised.exception))
            self.assertEqual(path.read_text(), original)


class TraversalTests(unittest.TestCase):
    def test_all_model_shapes(self):
        data = slim.parse(SAMPLE)
        paths = slim.model_paths(data)
        self.assertIn(("agents", "oracle", "model"), paths)
        self.assertIn(("presets", "base", "orchestrator", "model", 0), paths)
        self.assertIn(("presets", "base", "orchestrator", "model", 1), paths)
        self.assertIn(("presets", "openai", "oracle", "model", 0, "id"), paths)
        self.assertIn(("presets", "openai", "oracle", "model", 1, "id"), paths)

    def test_variant_and_fallback_options(self):
        data = slim.parse(SAMPLE)
        variants = slim.option_paths(data, "variant")
        self.assertIn(("presets", "base", "orchestrator", "variant"), variants)
        self.assertIn(("presets", "openai", "oracle", "model", 0, "variant"), variants)
        fallbacks = slim.option_paths(data, "fallback")
        self.assertEqual(fallbacks[("presets", "base", "orchestrator", "model", 1)], "base/fallback")
        self.assertEqual(fallbacks[("presets", "openai", "oracle", "model", 1, "id")], "openai/oracle-fb")

    def test_primary_detection_excludes_fallbacks(self):
        data = slim.parse(SAMPLE)
        primaries = [path for path in slim.model_paths(data) if slim.is_primary(path)]
        self.assertEqual(len(primaries), 5)
        for path in slim.option_paths(data, "fallback"):
            if "model" in path:
                self.assertFalse(slim.is_primary(path))


class ResolutionTests(unittest.TestCase):
    def test_extends_chain_and_root_override_precedence(self):
        data = slim.parse(SAMPLE)
        self.assertEqual(slim.preset_chain(data), ["base", "openai"])
        resolved = slim.effective_agents(data)
        # ancestor base -> child openai -> root agents
        self.assertEqual(slim.effective_model(resolved["orchestrator"]), "openai/primary")
        self.assertEqual(resolved["orchestrator"]["variant"], "medium")
        self.assertEqual(slim.effective_model(resolved["explorer"]), "base/explorer")
        self.assertEqual(slim.effective_model(resolved["oracle"]), "root/oracle")

    def test_inherit_model_from(self):
        data = slim.parse('{"agents":{"oracle":{"inheritModelFrom":"session"}}}')
        resolved = slim.effective_agents(data)
        self.assertEqual(slim.effective_model(resolved["oracle"]), "inherit:session")

    def test_inheritance_cycle_is_rejected(self):
        data = slim.parse('{"preset":"a","presets":{"a":{"extends":"b"},"b":{"extends":"a"}}}')
        with self.assertRaises(ValueError):
            slim.preset_chain(data)

    def test_nested_agents_form(self):
        data = slim.parse('{"presets":{"p":{"agents":{"oracle":{"model":"p/oracle"}}}}}')
        self.assertIn(("presets", "p", "agents", "oracle", "model"), slim.model_paths(data))


class WriteSafetyTests(unittest.TestCase):
    def test_primary_change_preserves_fallback_and_siblings(self):
        with temp_config() as path:
            slim.apply("new/oracle", agents=["presets/openai/oracle"], yes=True, known=["new/oracle"])
            data = slim.read()[1]
            first = data["presets"]["openai"]["oracle"]["model"][0]
            self.assertEqual(first["id"] if isinstance(first, dict) else first, "new/oracle")
            # Inline variant survives the change because only the model id is rewritten.
            self.assertEqual(first["variant"], "high")
            self.assertEqual(data["presets"]["openai"]["oracle"]["model"][1]["id"], "openai/oracle-fb")
            self.assertEqual(data["presets"]["base"]["orchestrator"]["model"][0], "base/primary")
            self.assertEqual(data["presets"]["openai"]["oracle"]["skills"], ["simplify"])
            self.assertTrue(data["other"])
            self.assertIn("// keep this comment", path.read_text())

    def test_all_entries_updates_only_primary_values(self):
        with temp_config() as path:
            slim.apply("new/all", all_entries=True, yes=True, known=["new/all"])
            data = slim.read()[1]
            self.assertEqual(data["presets"]["base"]["orchestrator"]["model"], ["new/all", "base/fallback"])
            self.assertEqual(data["presets"]["openai"]["oracle"]["model"][1]["id"], "openai/oracle-fb")

    def test_dry_run_keeps_file_byte_identical(self):
        with temp_config() as path:
            before = path.read_bytes()
            slim.apply("new/dry", all_entries=True, yes=True, dry_run=True, known=["new/dry"])
            self.assertEqual(path.read_bytes(), before)

    def test_edit_value_preserves_format_and_backs_up(self):
        with temp_config() as path:
            slim.edit_value(("presets", "base", "orchestrator", "variant"), "high", yes=True)
            self.assertEqual(slim.read()[1]["presets"]["base"]["orchestrator"]["variant"], "high")
            self.assertTrue(slim.backups())

    def test_file_mode_is_preserved(self):
        with temp_config() as path:
            os.chmod(path, 0o640)
            slim.apply("new/mode", all_entries=True, yes=True, known=["new/mode"])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    def test_symlink_target_is_updated_and_link_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            real = Path(folder) / "real.jsonc"
            real.write_text('{"agents":{"oracle":{"model":"old/model"}}}', encoding="utf-8")
            link = Path(folder) / "oh-my-opencode-slim.jsonc"
            link.symlink_to(real)
            with patch.object(slim, "CONFIG", link):
                slim.apply("new/model", all_entries=True, yes=True, known=["new/model"])
            self.assertTrue(link.is_symlink())
            self.assertEqual(json.loads(real.read_text())["agents"]["oracle"]["model"], "new/model")

    def test_unknown_target_is_rejected(self):
        with temp_config():
            with self.assertRaises(RuntimeError):
                slim.apply("new/x", agents=["does/not/exist"], yes=True, known=["new/x"])

    def test_restore_round_trip(self):
        with temp_config() as path:
            before = path.read_text()
            slim.apply("new/one", all_entries=True, yes=True, known=["new/one"])
            self.assertNotEqual(path.read_text(), before)
            slim.restore(before, yes=True)
            self.assertEqual(path.read_text(), before)


class DiscoveryTests(unittest.TestCase):
    def test_prefers_jsonc_over_json(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "oh-my-opencode-slim.json").write_text("{}")
            (base / "oh-my-opencode-slim.jsonc").write_text("{}")
            with patch.dict(os.environ, {"OMO_SLIM_CONFIG": "", "OPENCODE_CONFIG_DIR": folder}):
                with patch.object(slim, "CONFIG_DIR", base):
                    self.assertEqual(slim.config_path(), base / "oh-my-opencode-slim.jsonc")


if __name__ == "__main__":
    unittest.main()
