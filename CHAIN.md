# CHAIN.md — ASGARD code repo decision chain (lions_mane replay file)

@verify file:/home/doj/.config/xyz.chatboxapp.app/skills/asgard-os/ASGARD_SPEC.md
@verify file:/home/doj/.config/xyz.chatboxapp.app/skills/asgard-os/ASGARD_BUILD_PLAN.md
@verify file:/home/doj/.config/xyz.chatboxapp.app/skills/asgard-os/ASGARD_DIGEST_CORPUS.md

## N0 · ADR-001 (V) — 2026-10-10
Spec persisted + manual probe collection chosen over linter-first (weighted score 0.915).

## N1 · PHANTOM EXECUTION (V)
Cartography v9.1 (L0 + transversal loop), F1–F9 fixes produced by tabletop runs.

## N2 · REPROOF (V)
Six-lens cross-examination → ZTAF PASS WITH FLAGS → v1.2 corrections (downgraded claims,
exit criteria M1: linter by 2026-10-24 or park).

## N3 · BUILD PLAN (V)
ASGARD_BUILD_PLAN v1.0 → v1.1 (isotope-traced: corpus harvest, 9 rules, security allowlist).

## N4 · BUILD electra-d0 (V) — this commit
digest_lint.py (rules R1–R6/R8–R10) + Corpus A fixtures + adversarial tests + README.

## N5 · F10 ENTRYPOINT HYGIENE (V) — 2026-10-11
External smoke-test audit: router_seam.py destructured argv blindly — malformed invocations
(flags, empty task/class) emitted plausible digests with exit 0, violating the DoD
(2 = structural-malformation only) and the zero-trust axiom. Fix: guard empty/flag args → exit 2;
same guard applied to slot_capture (empty decision) + digest_gen (flag arg). 6 new entrypoint
fixtures (Corpus B gap closed: one fixture per RULE existed, none for the ENTRYPOINT).
