"""test_lint.py — electra-d0 test suite (stdlib unittest, no deps).

Corpus A = real session digests (fixtures). Corpus B = adversarial (inline).
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from electra.digest_lint import lint_file  # noqa: E402

FIX = pathlib.Path(__file__).parent / "fixtures"


def lint(path):
    return lint_file(str(path))


def write_tmp(content, binary=False):
    f = tempfile.NamedTemporaryFile("wb" if binary else "w", suffix=".md", delete=False)
    f.write(content.encode("latin-1") if binary and isinstance(content, str) else content)
    f.close()
    return f.name


class CorpusATests(unittest.TestCase):
    def test_v1_01_clean(self):
        r = lint(FIX / "DIGEST-V1-01.md")
        self.assertEqual(r["exit"], 0, r)

    def test_v1_02_clean(self):
        r = lint(FIX / "DIGEST-V1-02.md")
        self.assertEqual(r["exit"], 0, r)

    def test_pre01_historical_drift(self):
        r = lint(FIX / "DIGEST-PRE-01.md")
        self.assertEqual(r["exit"], 1)
        self.assertTrue(any("pre-v1" in f for f in r["findings"]))

    def test_pre02_historical_drift(self):
        r = lint(FIX / "DIGEST-PRE-02.md")
        self.assertEqual(r["exit"], 1)
        self.assertTrue(any("pre-v1" in f for f in r["findings"]))


class MalformedTests(unittest.TestCase):
    def test_empty_file(self):
        p = write_tmp("")
        self.assertEqual(lint_file(p)["exit"], 2)

    def test_not_utf8(self):
        p = write_tmp(b"\xff\xfe\x00bad", binary=True)
        self.assertEqual(lint_file(p)["exit"], 2)

    def test_oversize(self):
        p = write_tmp("I · x\n" * 600)
        self.assertEqual(lint_file(p)["exit"], 2)

    def test_no_registers(self):
        p = write_tmp("just prose here, nothing else\nsecond line\n")
        self.assertEqual(lint_file(p)["exit"], 2)


class AdversarialTests(unittest.TestCase):
    def test_probe_budget(self):
        p = write_tmp("\n".join(f"PROBE · risk · thing{i} (0.5) · basis: hunch" for i in range(4))
                      + "\nI · done.\nSYSTEM · 1 file pushed\nSLOT · none")
        r = lint_file(p)
        self.assertEqual(r["exit"], 1)
        self.assertTrue(any("budget" in f for f in r["findings"]))

    def test_probe_missing_basis(self):
        p = write_tmp("PROBE · risk · hunch (0.5)\nI · done.\nSYSTEM · 1 file pushed\nSLOT · none")
        self.assertTrue(any("basis" in f for f in lint_file(p)["findings"]))

    def test_i_too_long(self):
        p = write_tmp("\n".join(f"I · line {i}" for i in range(6)) + "\nSYSTEM · 1 pushed\nSLOT · none")
        self.assertTrue(any("exceeds 5" in f for f in lint_file(p)["findings"]))

    def test_system_first_person(self):
        p = write_tmp("I · done.\nSYSTEM · I think this is right\nSLOT · none")
        self.assertTrue(any("first-person" in f for f in lint_file(p)["findings"]))

    def test_missing_slot(self):
        p = write_tmp("I · done.\nSYSTEM · 1 file pushed")
        self.assertTrue(any("SLOT missing" in f for f in lint_file(p)["findings"]))

    def test_clinical_domain_needs_raw_read(self):
        p = write_tmp("domain: clinical\nI · reviewed.\nSYSTEM · 1 file pushed\nSLOT · none")
        r = lint_file(p)
        self.assertTrue(any("R6" in f for f in r["findings"]), r)

    def test_bad_digest_id(self):
        p = write_tmp("ID: not-a-hash\nI · done.\nSYSTEM · 1 file pushed\nSLOT · none")
        self.assertTrue(any("R8" in f for f in lint_file(p)["findings"]))

    def test_source_outside_allowlist(self):
        p = write_tmp("SOURCE: /etc/passwd\nI · done.\nSYSTEM · 1 file pushed\nSLOT · none")
        self.assertTrue(any("allowlist" in f for f in lint_file(p)["findings"]))

    def test_orphaned_source(self):
        p = write_tmp("SOURCE: ~/Desktop/Projects/nonexistent.md\nI · done.\nSYSTEM · 1 pushed\nSLOT · none")
        self.assertTrue(any("not found" in f for f in lint_file(p)["findings"]))

    def test_register_order(self):
        p = write_tmp("SYSTEM · 1 pushed\nI · done.\nSLOT · none")
        self.assertTrue(any("order" in f for f in lint_file(p)["findings"]))


class DeterminismTests(unittest.TestCase):
    def test_byte_identical_repeat_runs(self):
        out = [json.dumps(lint(FIX / "DIGEST-V1-01.md"), sort_keys=True) for _ in range(3)]
        self.assertEqual(out[0], out[1])
        self.assertEqual(out[1], out[2])


if __name__ == "__main__":
    unittest.main()
