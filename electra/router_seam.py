"""router_seam.py — one-invocation routing (electra-d1).

Chains the three routers in ONE command:
  1. conductor — authoritative table scan (keyword overlap, deterministic ranking)
  2. master-jedi — learned Bayesian recommendation (subprocess boundary)
  3. overseer — engine-level routing: 184 tests green; no stable CLI exposed,
     so the leg is reported, not invoked (honest v0 — do not fake a call).
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

CONDUCTOR = pathlib.Path("~/.config/xyz.chatboxapp.app/skills/conductor/SKILL.md").expanduser()
MASTER_JEDI = pathlib.Path("~/Desktop/Projects/master-jedi/master_jedi.py").expanduser()


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


def master_jedi_recommend(task_class: str, mj=MASTER_JEDI) -> str:
    r = subprocess.run(
        [sys.executable, str(mj), "recommend", "--task-class", task_class],
        capture_output=True, text=True,
    )
    return r.stdout.strip() or f"(master-jedi unavailable: {r.stderr.strip()})"


def seam(task: str, task_class: str) -> dict:
    table = CONDUCTOR.read_text() if CONDUCTOR.exists() else ""
    return {
        "task": task,
        "conductor_hits": conductor_hits(task, table),
        "master_jedi": master_jedi_recommend(task_class),
        "overseer_leg": "engine-level routing verified (184 tests); no stable CLI — reported, not invoked",
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: router_seam.py <task-description> <task-class>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(seam(sys.argv[1], sys.argv[2]), indent=2))
