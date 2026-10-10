"""tests for electra-d1: digest_gen, loop_hook, slot_capture, router_seam."""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "electra"))

from electra import digest_gen, slot_capture, router_seam  # noqa: E402

LINT = ROOT / "electra" / "digest_lint.py"


def lint_text(text: str) -> dict:
    p = pathlib.Path("/tmp/_d1_lint.md")
    p.write_text(text, encoding="utf-8")
    r = subprocess.run([sys.executable, str(LINT), str(p)],
                       capture_output=True, text=True)
    return json.loads(r.stdout), r.returncode


class TestDigestGen(unittest.TestCase):
    def spec(self, **kw):
        base = {
            "i": ["build the seam: one invocation, three routers."],
            "system": ["asgard repo pushed · 19 tests green · lagom 0.99"],
            "slot": "none — awaiting decision",
        }
        base.update(kw)
        return base

    def test_roundtrip_lints_clean(self):
        report, code = lint_text(digest_gen.generate(self.spec()))
        self.assertEqual(code, 0, report)

    def test_deterministic(self):
        a = digest_gen.generate(self.spec())
        b = digest_gen.generate(self.spec())
        self.assertEqual(a, b)

    def test_probe_emitted(self):
        d = digest_gen.generate(self.spec(probe={
            "class": "risk", "conjecture": "the seam will be used rarely",
            "confidence": 0.6, "basis": "routing is session-mediated today"}))
        self.assertIn('PROBE  · risk · "the seam will be used rarely" (0.60)', d)

    def test_confidence_range_enforced(self):
        with self.assertRaises(ValueError):
            digest_gen.generate(self.spec(probe={
                "conjecture": "x", "confidence": 1.7, "basis": "y"}))

    def test_i_cap_enforced(self):
        with self.assertRaises(ValueError):
            digest_gen.generate(self.spec(i=["a"] * 6))

    def test_high_stakes_domain_requires_raw_read(self):
        with self.assertRaises(ValueError):
            digest_gen.generate(self.spec(domain="clinical"))

    def test_source_missing_raises(self):
        with self.assertRaises(ValueError):
            digest_gen.generate(self.spec(source="/nonexistent/path"))


class TestLoopHook(unittest.TestCase):
    def test_hook_generates_and_lints(self):
        spec = pathlib.Path("/tmp/_d1_spec.json")
        spec.write_text(json.dumps({
            "i": ["persist the engineering spec, then sync everything."],
            "system": ["asgard repo pushed · anchor verified"],
            "slot": "none — awaiting decision",
        }))
        out = "/tmp/_d1_hook.md"
        rc = subprocess.run(
            [sys.executable, str(ROOT / "electra" / "loop_hook.py"), str(spec), out],
            capture_output=True, text=True,
        ).returncode
        self.assertEqual(rc, 0)
        self.assertIn("I      ·", pathlib.Path(out).read_text())


class TestSlotCapture(unittest.TestCase):
    def test_chain_integrity(self):
        ledger = pathlib.Path("/tmp/_d1_decisions.jsonl")
        ledger.unlink(missing_ok=True)
        slot_capture.capture("decide one", "test-agent", "d1", ledger)
        slot_capture.capture("decide two", "test-agent", "d2", ledger)
        ok, msg = slot_capture.verify(ledger)
        self.assertTrue(ok, msg)

    def test_tamper_detection(self):
        ledger = pathlib.Path("/tmp/_d1_decisions2.jsonl")
        ledger.unlink(missing_ok=True)
        slot_capture.capture("decide one", "a", "d1", ledger)
        lines = ledger.read_text().splitlines()
        e = json.loads(lines[0])
        e["decision"] = "TAMPERED"
        ledger.write_text(json.dumps(e) + "\n")
        ok, msg = slot_capture.verify(ledger)
        self.assertFalse(ok)
        self.assertIn("hash mismatch", msg)


class TestRouterSeam(unittest.TestCase):
    TABLE = (
        "| Code already on disk (audit/scan) | `lagom-engine` | never auto-run |\n"
        "| Job/grant applications | `fjap-ops` | never skip Phase 8 |\n"
        "| Input truth substrate for scorers | `anubis` | never exceed ceiling |\n"
    )

    def test_conductor_ranking(self):
        hits = router_seam.conductor_hits("please audit this python code", self.TABLE)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["skill"], "lagom-engine")

    def test_conductor_empty_on_no_overlap(self):
        hits = router_seam.conductor_hits("zzz qqq unrelated", self.TABLE)
        self.assertEqual(hits, [])

    def test_overseer_leg_subprocess_boundary(self):
        fake = pathlib.Path("/tmp/_fake_overseer_cli.py")
        fake.write_text(
            "import json,sys\nprint(json.dumps({'engine': 'ema', 'domain': 'clinical_only'}))\n"
        )
        r = router_seam.overseer_route("patient numbness", cli=fake)
        self.assertEqual(r["engine"], "ema")

    def test_overseer_leg_fallback(self):
        r = router_seam.overseer_route("anything", cli=pathlib.Path("/tmp/_missing_cli.py"))
        self.assertEqual(r["engine"], "unavailable")


class TestEntrypointHygiene(unittest.TestCase):
    """F10: malformed entrypoint → exit 2, never plausible output."""
    SEAM = ROOT / "electra" / "router_seam.py"
    SLOT = ROOT / "electra" / "slot_capture.py"
    GEN = ROOT / "electra" / "digest_gen.py"

    def _rc(self, script, *args):
        return subprocess.run(
            [sys.executable, str(script), *args], capture_output=True, text=True
        ).returncode

    def test_seam_flag_arg_rejected(self):
        self.assertEqual(self._rc(self.SEAM, "--text", "audit this codebase"), 2)

    def test_seam_empty_task_rejected(self):
        self.assertEqual(self._rc(self.SEAM, "", "code_audit"), 2)

    def test_seam_empty_class_rejected(self):
        self.assertEqual(self._rc(self.SEAM, "task", ""), 2)

    def test_seam_extra_args_rejected(self):
        self.assertEqual(self._rc(self.SEAM, "t", "c", "extra"), 2)

    def test_slot_empty_decision_rejected(self):
        self.assertEqual(self._rc(self.SLOT, "", "agent"), 2)

    def test_digest_gen_flag_rejected(self):
        self.assertEqual(self._rc(self.GEN, "--help"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
