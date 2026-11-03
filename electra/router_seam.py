"""router_seam.py — one-invocation routing (electra-d1).

Chains the three routers in ONE command:
  1. conductor — authoritative table scan (keyword overlap, deterministic ranking)
  2. master-jedi — learned Bayesian recommendation (subprocess boundary)
  3. overseer — engine-level routing via its W1 CLI (subprocess; graceful fallback)
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys


def _resolve(key: str, candidates, legacy=None) -> pathlib.Path:
    """Env override -> workspace discovery -> legacy (gated). Fail closed with
    the searched list: never silently guess (zero-trust audit 2026-11-03)."""
    if os.environ.get(key):
        return pathlib.Path(os.environ[key]).expanduser()
    root = pathlib.Path(os.environ.get("PROJECTS_ROOT", "~/Desktop/Projects")).expanduser()
    for c in candidates:
        p = root / c
        if p.exists():
            return p
    if legacy and os.environ.get("ALLOW_LEGACY_CHATBOX") == "1":
        p = pathlib.Path(legacy).expanduser()
        if p.exists():
            print("USING_LEGACY_CHATBOX_PATH: %s" % p, file=sys.stderr)
            return p
    raise FileNotFoundError(
        "UNRESOLVED:%s searched=%s root=%s (set %s, PROJECTS_ROOT, or ALLOW_LEGACY_CHATBOX=1)"
        % (key, candidates, root, key))


CONDUCTOR = _resolve("CONDUCTOR_PATH", ["cognitive-skills/conductor/SKILL.md"],
                     "~/.config/xyz.chatboxapp.app/skills/conductor/SKILL.md")
MASTER_JEDI = _resolve("MASTER_JEDI_PATH", ["master-jedi/master_jedi.py"])
OVERSEER_CLI = _resolve("OVERSEER_CLI_PATH", ["overseer/orchestrator/cli.py"])


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


OVERSEER_ROUTE_KEYS = {"task", "domain", "engine", "escalate"}


def overseer_route(task: str, cli=OVERSEER_CLI) -> dict:
    """W1: overseer's callable mouth. Subprocess boundary; graceful fallback.
    Schema-guarded: output missing required keys = contract drift, rejected
    (fail-closed, never half-consumed)."""
    if not cli.exists():
        return {"engine": "unavailable", "reason": f"overseer CLI not found: {cli}"}
    r = subprocess.run(
        [sys.executable, str(cli), task], capture_output=True, text=True
    )
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
