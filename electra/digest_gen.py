"""digest_gen.py — Electra's writer (electra-d1).

Structured spec → conforming digest. Formatting lives HERE; RULES live in
digest_lint.py (single source — no duplication). The loop hook chains both:
generate → write → lint. Deterministic: same spec → byte-identical digest.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys


def _pad(token: str) -> str:
    return f"{token:<7s}"


def generate(spec: dict) -> str:
    lines: list[str] = []
    # PROBE (optional; ≤3 enforced by linter, budget respected by caller)
    if spec.get("probe"):
        p = spec["probe"]
        conf = float(p.get("confidence", 0.5))
        if not (0.0 <= conf <= 1.0):
            raise ValueError(f"probe confidence out of range: {conf}")
        cls = p.get("class", "risk")
        lines.append(f'{_pad("PROBE")}· {cls} · "{p["conjecture"]}" ({conf:.2f})')
        lines.append(f'       · basis: {p.get("basis") or "no basis"}')
    # I register (required, ≤5)
    i_lines = spec.get("i", [])
    if not i_lines:
        raise ValueError("I register required (adjutant voice)")
    if len(i_lines) > 5:
        raise ValueError(f"I register exceeds 5 lines: {len(i_lines)}")
    for ln in i_lines:
        lines.append(f'{_pad("I")}· {ln}')
    # SYSTEM register (required)
    sys_lines = spec.get("system", [])
    if not sys_lines:
        raise ValueError("SYSTEM register required (reporter voice)")
    for j, ln in enumerate(sys_lines):
        lines.append(f'{_pad("SYSTEM") if j == 0 else "       "}· {ln}')
    # optional ID/SOURCE (R8 — drift detection)
    src = spec.get("source")
    if src:
        p = pathlib.Path(src).expanduser()
        if not p.exists():
            raise ValueError(f"source not found: {src}")
        lines.append(f'ID: {hashlib.sha256(p.read_bytes()).hexdigest()}')
        lines.append(f'SOURCE: {src}')
    # optional high-stakes domain + raw-read instruction (R6)
    dom = spec.get("domain")
    if dom:
        lines.append(f'domain: {dom}')
        if dom.lower() in ("clinical", "legal", "manuscript"):
            if not spec.get("raw_read"):
                raise ValueError("high-stakes domain requires raw_read instruction")
            lines.append(f'raw-read: {spec["raw_read"]}')
    # SLOT (required; explicit null is valid)
    slot = spec.get("slot")
    lines.append(f'{_pad("SLOT")}· {slot if slot is not None else "none — awaiting decision"}')
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        if argv[1].startswith("-"):
            print("usage: digest_gen.py [spec.json] (or JSON on stdin)", file=sys.stderr)
            return 2
        spec = json.load(open(argv[1]))
    else:
        spec = json.load(sys.stdin)
    print(generate(spec), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
