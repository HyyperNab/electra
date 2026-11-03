"""resolver.py — unified path resolver for the ASGARD Python surface (electra-d2).

Single implementation of the discovery contract (one engine per job; a second
copy is a divergence SPOF):

    1. env override       — <COMPONENT>_PATH set? use it, expanded.
    2. workspace discovery — PROJECTS_ROOT/<candidate> must exist on disk.
    3. legacy gate        — only when ALLOW_LEGACY_CHATBOX=1 AND the legacy
                            path exists (never silently).
    4. fail closed        — UNRESOLVED error names every path checked.

MOAC SIBLING (JavaScript): moac/server/index.js implements the same contract
in JS — env (MOAC_ROOT/MOAC_PORT/MOAC_HOST) -> discovery (repo root, never a
hardcoded home path) -> fail-closed exit 2, loopback default with non-loopback
refusal (MOAC_ALLOW_NONLOCAL=1), boot forensics line. The contract is
language-agnostic; both implementations must keep: env-first, discovery over
hardcoded paths, legacy only behind an explicit gate, fail-closed errors that
name what was searched, loopback-by-default binds.

COMPONENTS table: name -> {key: env var, candidates: [PROJECTS_ROOT-relative],
legacy?: chatbox-config path gated by ALLOW_LEGACY_CHATBOX}.
"""
from __future__ import annotations

import os
import pathlib
import sys

COMPONENTS = {
    "conductor": {
        "key": "CONDUCTOR_PATH",
        "candidates": ["cognitive-skills/conductor/SKILL.md"],
        "legacy": "~/.config/xyz.chatboxapp.app/skills/conductor/SKILL.md",
    },
    "master_jedi": {
        "key": "MASTER_JEDI_PATH",
        "candidates": ["master-jedi/master_jedi.py"],
    },
    "overseer_cli": {
        "key": "OVERSEER_CLI_PATH",
        "candidates": ["overseer/orchestrator/cli.py"],
    },
    "janitor": {
        "key": "JANITOR_PATH",
        "candidates": ["cognitive-skills/janitor/tools/janitor.py"],
    },
    "session": {
        "key": "SESSION_PATH",
        "candidates": ["cognitive-skills/tools/session.py"],
    },
    "skill_guard": {
        "key": "SKILL_GUARD_PATH",
        "candidates": ["cognitive-skills/tools/skill_guard.py"],
    },
}


def _resolve(key: str, candidates, legacy=None) -> pathlib.Path:
    """Env override -> workspace discovery -> legacy (gated). Fail closed with
    the searched list: never silently guess (zero-trust audit 2026-11-03)."""
    if os.environ.get(key):
        return pathlib.Path(os.environ[key]).expanduser()
    root = pathlib.Path(os.environ.get("PROJECTS_ROOT", "~/Desktop/Projects")).expanduser()
    searched = [root / c for c in candidates]
    for p in searched:
        if p.exists():
            return p
    if legacy and os.environ.get("ALLOW_LEGACY_CHATBOX") == "1":
        p = pathlib.Path(legacy).expanduser()
        if p.exists():
            print("USING_LEGACY_CHATBOX_PATH: %s" % p, file=sys.stderr)
            return p
    checked = ", ".join(str(s) for s in searched)
    legacy_note = " legacy=%s" % legacy if legacy else ""
    raise FileNotFoundError(
        "UNRESOLVED:%s checked=[%s]%s root=%s "
        "(set %s, PROJECTS_ROOT, or ALLOW_LEGACY_CHATBOX=1)"
        % (key, checked, legacy_note, root, key))


def resolve(name: str) -> pathlib.Path:
    """Resolve a component by table name. Unknown name = KeyError (fail closed,
    never a guessed default)."""
    spec = COMPONENTS[name]
    return _resolve(spec["key"], spec["candidates"], spec.get("legacy"))


def resolve_all() -> dict:
    """Resolve every component; {name: str(path)}. Unresolvable components are
    reported as 'UNRESOLVED: …' strings, never omitted or guessed."""
    out = {}
    for name in COMPONENTS:
        try:
            out[name] = str(resolve(name))
        except FileNotFoundError as e:
            out[name] = "UNRESOLVED: %s" % e
    return out


# Import-time bindings (router_seam's public constants, unchanged).
CONDUCTOR = resolve("conductor")
MASTER_JEDI = resolve("master_jedi")
OVERSEER_CLI = resolve("overseer_cli")


if __name__ == "__main__":
    import json

    print(json.dumps(resolve_all(), indent=2))
