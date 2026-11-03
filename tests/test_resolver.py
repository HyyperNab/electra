"""tests for electra-d2: unified resolver (env -> discovery -> gated legacy)."""
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from electra.resolver import COMPONENTS, _resolve, resolve, resolve_all  # noqa: E402


class TestResolveCore(unittest.TestCase):
    def setUp(self):
        self._saved = {}
        for k in ("PROJECTS_ROOT", "ALLOW_LEGACY_CHATBOX", "CONDUCTOR_PATH"):
            if k in os.environ:
                self._saved[k] = os.environ[k]
                del os.environ[k]

    def tearDown(self):
        for k in ("PROJECTS_ROOT", "ALLOW_LEGACY_CHATBOX", "CONDUCTOR_PATH"):
            os.environ.pop(k, None)
        os.environ.update(self._saved)

    def test_env_override_wins(self):
        with tempfile.TemporaryDirectory() as td:
            f = pathlib.Path(td) / "x.md"
            f.write_text("x")
            os.environ["CONDUCTOR_PATH"] = str(f)
            self.assertEqual(_resolve("CONDUCTOR_PATH", ["nope/nope.md"]), f)

    def test_discovery_under_projects_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "cognitive-skills" / "conductor").mkdir(parents=True)
            sk = root / "cognitive-skills" / "conductor" / "SKILL.md"
            sk.write_text("t")
            os.environ["PROJECTS_ROOT"] = str(root)
            self.assertEqual(
                _resolve("CONDUCTOR_PATH", ["cognitive-skills/conductor/SKILL.md"]), sk)

    def test_legacy_gated(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            legacy = root / "legacy.md"
            legacy.write_text("t")
            os.environ["PROJECTS_ROOT"] = str(root / "empty")
            # gate off -> fail closed even though legacy exists
            with self.assertRaises(FileNotFoundError):
                _resolve("CONDUCTOR_PATH", ["cognitive-skills/conductor/SKILL.md"],
                         legacy=str(legacy))
            # gate on -> legacy used
            os.environ["ALLOW_LEGACY_CHATBOX"] = "1"
            self.assertEqual(
                _resolve("CONDUCTOR_PATH", ["cognitive-skills/conductor/SKILL.md"],
                         legacy=str(legacy)),
                legacy)

    def test_fail_closed_lists_checked(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["PROJECTS_ROOT"] = str(pathlib.Path(td))
            with self.assertRaises(FileNotFoundError) as ctx:
                _resolve("CONDUCTOR_PATH", ["cognitive-skills/conductor/SKILL.md"])
            msg = str(ctx.exception)
            self.assertIn("UNRESOLVED:CONDUCTOR_PATH", msg)
            self.assertIn("cognitive-skills/conductor/SKILL.md", msg)
            self.assertIn("ALLOW_LEGACY_CHATBOX=1", msg)

    def test_unknown_component_keyerror(self):
        with self.assertRaises(KeyError):
            resolve("no_such_component")

    def test_resolve_all_never_omits(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["PROJECTS_ROOT"] = str(pathlib.Path(td))
            out = resolve_all()
            self.assertEqual(set(out), set(COMPONENTS))
            self.assertTrue(all(str(v).startswith("UNRESOLVED:") for v in out.values()))

    def test_resolve_all_real_workspace(self):
        # default PROJECTS_ROOT (~/Desktop/Projects) must resolve the core trio
        out = resolve_all()
        for name in ("conductor", "master_jedi", "overseer_cli", "janitor", "session"):
            self.assertFalse(str(out[name]).startswith("UNRESOLVED:"), (name, out[name]))


if __name__ == "__main__":
    unittest.main()
