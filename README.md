# ELECTRA — the interface function protocol

ELECTRA is the interface function of the ASGARD cognitive OS. It is **not** the OS itself — it is the protocol through which the OS interfaces with the world: intake probes, digest generation/compression, loop hooks, and slot capture. Built per ASGARD_BUILD_PLAN v1.1 (six-sigma funnel, SPOF-registered). Stdlib-only, zero deps, deterministic.

## Electra v3 — the interface function

```
electra(mode, payload) → digest     modes: digest · teach · trace · status
wake-on: pipeline-complete · gate-verdict · invocation · daily heartbeat
wake-off: emit → gone. No daemon. State = disk (chains, CHANGELOG, memory).
```

**Four registers (epistemic ladder):**
| Register | Moment | Class | Rules |
|---|---|---|---|
| **PROBE** | intake, pre-analysis | CONJECTURE (pre-registered) | ≤3/task · confidence + basis cited · **never gates** · scored post-outcome |
| **I** | post-analysis | JUDGED (attributed) | ≤5 lines · action-first · opinions labeled hers |
| **SYSTEM** | post-analysis | MEASURED/RETRIEVED | compress, never add · every line traceable |
| **SLOT** | close | DECISION (human) | answer re-enters the record as an attested input |

Digest cycle: **PROBE → I → SYSTEM → SLOT**, closed when the human answer is logged.

## λ table (compression governor)
ideation 1.5 · code/ops 1.0 · strategy 0.7 · clinical/legal/manuscripts **0.3** (near-verbatim + raw-read instruction).

## Code

- `electra/digest_lint.py` — the linter: rules R1–R10, exit codes 0/1/2, @verify-style source checks, allowlist roots, byte-identical repeat output.
- `electra/digest_gen.py` — the generator: produces PROBE/I/SYSTEM/SLOT digests from raw input.
- `electra/loop_hook.py` — hooks into pipeline-complete / gate-verdict / invocation events.
- `electra/slot_capture.py` — captures human decisions, logs them as attested inputs.
- `electra/router_seam.py` — subprocess boundary seam: conductor + master-jedi + overseer converge for code_audit.
- `tests/` — Corpus A (real session digests) + Corpus B (adversarial, one per F-fix + edge cases) + determinism test.

```bash
python3 electra/digest_lint.py tests/fixtures/DIGEST-V1-01.md   # expect exit 0
python3 -m unittest discover -s tests -q                        # expect all green
```

## Build state (verified 2026-10-11)
electra-d0 (linter) → electra-d1 (generator + loop hook + slot capture + router seam) all BUILT. F10 entrypoint-hygiene fix landed. Seam has 3 live subprocess legs (conductor + master-jedi + overseer). Build queue empty.
