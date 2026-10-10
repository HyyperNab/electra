# ASGARD — the OS code repo (electra-d0)

First increment of the ASGARD L0 interface layer. Built per ASGARD_BUILD_PLAN v1.1
(six-sigma funnel, SPOF-registered). Stdlib-only, zero deps, deterministic.

- `electra/digest_lint.py` — the linter: rules R1–R6/R8–R10, exit codes 0/1/2,
  @verify-style source checks, allowlist roots, byte-identical repeat output.
- `tests/` — Corpus A (real session digests, harvested) + Corpus B (adversarial,
  one per F-fix + edge cases) + determinism test.

```bash
python3 electra/digest_lint.py tests/fixtures/DIGEST-V1-01.md   # expect exit 0
python3 -m unittest discover -s tests -q                        # expect all green
```

Deadline (M1): 2026-10-24. Parking pauses doctrine only; partials persist.
