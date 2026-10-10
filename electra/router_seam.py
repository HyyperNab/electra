"""router_seam.py — one-invocation routing (electra-d1).

Chains the three routers in ONE command:
  1. conductor — authoritative table scan (keyword overlap, deterministic ranking)
  2. master-jedi — learned Bayesian recommendation (subprocess boundary)
  3. overseer — engine-level routing via its W1 CLI (subprocess; graceful fallback)
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

CONDUCTOR = pathlib.Path("~/.config/xyz.chatboxapp.app/skills/conductor/SKILL.md").expanduser()
MASTER_JEDI = pathlib.Path("~/Desktop/Projects/master-jedi/master_jedi.py").expanduser()
OVERSEER_CLI = pathlib.Path("~/Desktop/Projects/overseer/orchestrator/cli.py").expanduser()


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


def overseer_route(task: str, cli=OVERSEER_CLI) -> dict:
    """W1: overseer's callable mouth. Subprocess boundary; graceful fallback."""
    if not cli.exists():
        return {"engine": "unavailable", "reason": f"overseer CLI not found: {cli}"}
    r = subprocess.run(
        [sys.executable, str(cli), task], capture_output=True, text=True
    )
    if r.returncode != 0:
        return {"engine": "unavailable", "reason": (r.stderr or "error").strip()[:200]}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"engine": "unavailable", "reason": "unparseable overseer output"}


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
