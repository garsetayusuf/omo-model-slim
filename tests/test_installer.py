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


def make_source(folder: Path, version: str = "1.0.5") -> Path:
    source = folder / "source"
    source.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        text = (ROOT / name).read_text(encoding="utf-8")
        text = text.replace('VERSION = "1.0.5"', f'VERSION = "{version}"') if name == "omo_model_slim.py" else text
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
            "OMO_VERSION": "v1.0.5",
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
        self.assertIn("OMO Manager", result.stdout)
        self.assertIn("Install complete", result.stdout)
        self.assertIn("Download & checksums", result.stdout)
        version = subprocess.run([str(wrapper), "--version"], capture_output=True, text=True)
        self.assertEqual(version.stdout.strip(), "omo-model-slim 1.0.5")
        verified = self.run_installer("verify")
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        self.assertIn("Installation is healthy", verified.stdout)

    def test_existing_omo_model_is_never_touched(self):
        original = self.prefix / "bin" / "omo-model"
        self.prefix.joinpath("bin").mkdir(parents=True)
        original.write_text("#!/bin/sh\necho original\n", encoding="utf-8")
        before = original.read_bytes()
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(original.read_bytes(), before)
        self.assertTrue((self.prefix / "bin" / "omo-model-slim").is_file())

    def test_checksum_mismatch_aborts_install(self):
        (self.source / "omo_tui.py").write_text("# tampered\n")
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum", result.stdout + result.stderr)
        self.assertFalse((self.prefix / "bin" / "omo-model-slim").exists())

    def test_same_version_reports_already_up_to_date(self):
        self.assertEqual(self.run_installer().returncode, 0)
        before = list((self.prefix / "share").glob("omo-model-slim.rollback.*"))
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Already up to date", result.stdout)
        self.assertIn("OMO_FORCE=1", result.stdout)
        self.assertNotIn("complete", result.stdout)
        self.assertEqual(list((self.prefix / "share").glob("omo-model-slim.rollback.*")), before)

    def test_force_reinstalls_same_version(self):
        self.assertEqual(self.run_installer().returncode, 0)
        env = {**self.env, "OMO_FORCE": "1"}
        result = self.run_installer(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reinstall complete", result.stdout)
        self.assertTrue(list((self.prefix / "share").glob("omo-model-slim.rollback.*")))

    def test_upgrade_keeps_rollback_copy(self):
        self.assertEqual(self.run_installer().returncode, 0)
        upgraded = make_source(self.base / "upgrade", version="1.0.6")
        env = {**self.env, "OMO_BASE_URL": upgraded.as_uri(), "OMO_VERSION": "v1.0.6"}
        result = self.run_installer(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        version = subprocess.run([str(self.prefix / "bin" / "omo-model-slim"), "--version"], capture_output=True, text=True)
        self.assertEqual(version.stdout.strip(), "omo-model-slim 1.0.6")
        self.assertTrue(list((self.prefix / "share").glob("omo-model-slim.rollback.*")))
        self.assertIn("rollback", result.stdout)

    def test_uninstall_removes_only_omo_model_slim(self):
        self.assertEqual(self.run_installer().returncode, 0)
        result = self.run_installer("uninstall")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.prefix / "bin" / "omo-model-slim").exists())
        self.assertFalse((self.prefix / "share" / "omo-model-slim").exists())

    def test_plain_mode_has_no_ansi_and_uses_text_markers(self):
        env = {**self.env, "NO_COLOR": "1"}
        result = self.run_installer(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("\033[", result.stdout)
        self.assertIn("OK Install complete", result.stdout)

    def test_forced_color_mode_emits_ansi(self):
        env = {**self.env, "OMO_COLOR": "1"}
        result = self.run_installer(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("\033[", result.stdout)
        self.assertNotIn("\\033[", result.stdout)  # no literal escape text may leak
        self.assertIn("Install complete", result.stdout)

    def test_uninstall_cleans_path_entries_and_backs_up_profile(self):
        home = self.base / "homedir"
        home.mkdir()
        profile = home / ".zshrc"
        profile.write_text(
            '# shell config\nalias ll="ls -l"\n'
            'export PATH="' + str(self.prefix / "bin") + ':$PATH"\n'
            'export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH\n',
            encoding="utf-8",
        )
        env = {**self.env, "HOME": str(home)}
        self.assertEqual(self.run_installer(env=env).returncode, 0)
        result = self.run_installer("uninstall", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("shell profile(s) cleaned", result.stdout)
        self.assertNotIn(str(self.prefix / "bin"), profile.read_text())
        self.assertIn('alias ll="ls -l"', profile.read_text())
        self.assertIn('export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH', profile.read_text())
        self.assertTrue(list(home.glob(".zshrc.omo-bak.*")))

    def test_uninstall_surgically_removes_only_omo_segment(self):
        home = self.base / "homedir3"
        home.mkdir()
        profile = home / ".zshrc"
        profile.write_text('export PATH="/opt/bin:' + str(self.prefix / "bin") + ':$PATH"\n', encoding="utf-8")
        env = {**self.env, "HOME": str(home)}
        self.assertEqual(self.run_installer(env=env).returncode, 0)
        result = self.run_installer("uninstall", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(profile.read_text(), 'export PATH="/opt/bin:$PATH"\n')

    def test_uninstall_handles_default_home_path_form(self):
        home = self.base / "homedir4"
        home.mkdir()
        profile = home / ".zshrc"
        profile.write_text('export PATH="$HOME/bin:$HOME/.local/bin:$PATH"\n', encoding="utf-8")
        env = {**self.env, "HOME": str(home), "PREFIX": str(home / ".local")}
        self.assertEqual(self.run_installer(env=env).returncode, 0)
        result = self.run_installer("uninstall", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(profile.read_text(), 'export PATH="$HOME/bin:$PATH"\n')

    def test_uninstall_keeps_path_when_bin_still_has_files(self):
        home = self.base / "homedir2"
        home.mkdir()
        profile = home / ".bashrc"
        line = 'export PATH="' + str(self.prefix / "bin") + ':$PATH"\n'
        profile.write_text(line, encoding="utf-8")
        env = {**self.env, "HOME": str(home)}
        self.assertEqual(self.run_installer(env=env).returncode, 0)
        (self.prefix / "bin" / "other-tool").write_text("#!/bin/sh\n", encoding="utf-8")
        result = self.run_installer("uninstall", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("still contains other executables", result.stdout)
        self.assertIn(line, profile.read_text())

    def test_wsl_is_detected(self):
        stub = self.base / "bin"
        stub.mkdir()
        uname = stub / "uname"
        uname.write_text('#!/bin/sh\ncase "$1" in -s) echo Linux;; -r) echo 5.15.0-microsoft-standard-WSL2;; *) echo Linux;; esac\n', encoding="utf-8")
        uname.chmod(0o755)
        env = {**self.env, "PATH": f"{stub}:{os.environ['PATH']}"}
        result = self.run_installer(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Platform detected", result.stdout)
        self.assertIn("WSL", result.stdout)


if __name__ == "__main__":
    unittest.main()
