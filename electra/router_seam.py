"""router_seam.py — one-invocation routing (electra-d1).

Chains the three routers in ONE command:
  1. conductor — authoritative table scan (keyword overlap, deterministic ranking)
  2. master-jedi — learned Bayesian recommendation (subprocess boundary)
  3. overseer — engine-level routing via its W1 CLI (subprocess; graceful fallback)

Path resolution is delegated to electra.resolver (unified discovery contract);
this module owns routing logic only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

try:  # module context (tests, imports)
    from electra.resolver import CONDUCTOR, MASTER_JEDI, OVERSEER_CLI
except ImportError:  # script context (python3 electra/router_seam.py)
    from resolver import CONDUCTOR, MASTER_JEDI, OVERSEER_CLI


def conductor_hits(task: str, table_text: str, top: int = 3) -> list[dict]:
    rows = re.findall(r"\|\s*(.+?)\s*\|\s*`([^`]+)`\s*\|[^|]*\|", table_text)
    words = set(re.findall(r"[a-z0-9]{3,}", task.lower()))
    scored = []
    for desc, skill in rows:
        dw = set(re.findall(r"[a-z0-9]{3,}", desc.lower()))
        overlap = len(words & dw)
        if overlap:
            scored.append((overlap, desc.strip(), skill))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [{"overlap": s[0], "description": s[1], "skill": s[2]} for s in scored[:top]]


def _subprocess_timeout() -> float:
    """ROUTE-001: bound every subprocess call; a hung CLI must not hang the seam."""
    try:
        t = float(os.environ.get("ROUTE_SUBPROCESS_TIMEOUT", "10"))
        return t if t > 0 else 10.0
    except ValueError:
        return 10.0


def master_jedi_recommend(task_class: str, mj=MASTER_JEDI) -> str:
    cmd = [sys.executable, str(mj), "recommend", "--task-class", task_class]
    t = _subprocess_timeout()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
    except subprocess.TimeoutExpired:
        return f"(master-jedi timeout after {t:g}s: {' '.join(cmd)})"
    return r.stdout.strip() or f"(master-jedi unavailable: {r.stderr.strip()})"


OVERSEER_ROUTE_KEYS = {"task", "domain", "engine", "escalate"}


def overseer_route(task: str, cli=OVERSEER_CLI) -> dict:
    """W1: overseer's callable mouth. Subprocess boundary; graceful fallback.
    Schema-guarded: output missing required keys = contract drift, rejected
    (fail-closed, never half-consumed)."""
    if not cli.exists():
        return {"engine": "unavailable", "reason": f"overseer CLI not found: {cli}"}
    cmd = [sys.executable, str(cli), task]
    t = _subprocess_timeout()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
    except subprocess.TimeoutExpired:
        return {"engine": "unavailable",
                "reason": f"overseer CLI timeout after {t:g}s: {' '.join(cmd)}"}
    if r.returncode != 0:
        return {"engine": "unavailable", "reason": (r.stderr or "error").strip()[:200]}
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"engine": "unavailable", "reason": "unparseable overseer output"}
    missing = OVERSEER_ROUTE_KEYS - data.keys()
    if missing:
        return {"engine": "unavailable",
                "reason": f"overseer contract drift — missing keys: {sorted(missing)}"}
    return data


def seam(task: str, task_class: str) -> dict:
    table = CONDUCTOR.read_text() if CONDUCTOR.exists() else ""
    return {
        "task": task,
        "conductor_hits": conductor_hits(task, table),
        "master_jedi": master_jedi_recommend(task_class),
        "overseer": overseer_route(task),
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: router_seam.py <task-description> <task-class>", file=sys.stderr)
        sys.exit(2)
    task, cls = sys.argv[1], sys.argv[2]
    # F10: malformed entrypoint → reject, never emit plausible output.
    if (not task.strip() or not cls.strip()
            or task.startswith("-") or cls.startswith("-")):
        print("usage: router_seam.py <task-description> <task-class>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(seam(task, cls), indent=2))
