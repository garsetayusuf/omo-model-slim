"""End-to-end installer smoke tests using a local artifact source."""

import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ("omo-model-slim", "omo_model_slim.py", "omo_tui.py", "opencode_manage.py", "install.sh")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_source(folder: Path, version: str = "1.0.1") -> Path:
    source = folder / "source"
    source.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        text = (ROOT / name).read_text(encoding="utf-8")
        text = text.replace('VERSION = "1.0.1"', f'VERSION = "{version}"') if name == "omo_model_slim.py" else text
        (source / name).write_text(text, encoding="utf-8")
    manifest = "".join(f"{sha256(source / name)}  {name}\n" for name in FILES)
    (source / "SHA256SUMS").write_text(manifest, encoding="utf-8")
    return source


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = make_source(self.base)
        self.prefix = self.base / "prefix"
        self.env = {
            **os.environ,
            "OMO_BASE_URL": self.source.as_uri(),
            "OMO_VERSION": "v1.0.1",
            "PREFIX": str(self.prefix),
        }

    def run_installer(self, *args, env=None):
        return subprocess.run(
            ["sh", str(ROOT / "install.sh"), *args],
            env=env or self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_fresh_install_and_verification(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        wrapper = self.prefix / "bin" / "omo-model-slim"
        self.assertTrue(wrapper.is_file())
        self.assertTrue(wrapper.stat().st_mode & stat.S_IXUSR)
        version = subprocess.run([str(wrapper), "--version"], capture_output=True, text=True)
        self.assertEqual(version.stdout.strip(), "omo-model-slim 1.0.1")
        verified = self.run_installer("verify")
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

    def test_existing_omo_model_is_never_touched(self):
        original = self.prefix / "bin" / "omo-model"
        self.prefix.joinpath("bin").mkdir(parents=True)
        original.write_text("#!/bin/sh\necho original\n", encoding="utf-8")
        before = original.read_bytes()
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(original.read_bytes(), before)
        self.assertIn("not modified", result.stdout)

    def test_checksum_mismatch_aborts_install(self):
        (self.source / "omo_tui.py").write_text("# tampered\n")
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum", result.stdout + result.stderr)
        self.assertFalse((self.prefix / "bin" / "omo-model-slim").exists())

    def test_upgrade_keeps_rollback_copy(self):
        self.assertEqual(self.run_installer().returncode, 0)
        upgraded = make_source(self.base / "upgrade", version="1.0.2")
        env = {**self.env, "OMO_BASE_URL": upgraded.as_uri()}
        result = self.run_installer(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        version = subprocess.run([str(self.prefix / "bin" / "omo-model-slim"), "--version"], capture_output=True, text=True)
        self.assertEqual(version.stdout.strip(), "omo-model-slim 1.0.2")
        self.assertTrue(list((self.prefix / "share").glob("omo-model-slim.rollback.*")))
        self.assertIn("rollback", result.stdout)

    def test_uninstall_removes_only_omo_model_slim(self):
        self.assertEqual(self.run_installer().returncode, 0)
        result = self.run_installer("uninstall")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.prefix / "bin" / "omo-model-slim").exists())
        self.assertFalse((self.prefix / "share" / "omo-model-slim").exists())

    def test_wsl_is_detected(self):
        stub = self.base / "bin"
        stub.mkdir()
        uname = stub / "uname"
        uname.write_text('#!/bin/sh\ncase "$1" in -s) echo Linux;; -r) echo 5.15.0-microsoft-standard-WSL2;; *) echo Linux;; esac\n', encoding="utf-8")
        uname.chmod(0o755)
        env = {**self.env, "PATH": f"{stub}:{os.environ['PATH']}"}
        result = self.run_installer(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("platform: WSL", result.stdout)


if __name__ == "__main__":
    unittest.main()
