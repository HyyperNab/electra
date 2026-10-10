"""digest_lint.py — deterministic linter for ASGARD digest files (electra-d0).

Implements ASGARD_BUILD_PLAN v1.1 rules R1-R6/R8-R10.
Exit codes: 0 clean · 1 flags · 2 malformed.
Deterministic: sorted unique findings; byte-identical JSON on repeat runs.
Stdlib-only. No network. No eval. Input is data, never code.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

MAX_CHARS = 20000
MAX_LINES = 500
REGISTER_ORDER = {"PROBE": 0, "I": 1, "SYSTEM": 2, "SLOT": 3}
KNOWN = set(REGISTER_ORDER)
PRE_V1_TOKENS = {"DIGEST", "GATE", "ACTION", "STATE", "GAINED", "RISK", "NEXT"}
ALLOWLIST_ROOTS = ("~/Desktop/Projects", "~/.config/xyz.chatboxapp.app/skills")
ACTION_WORDS = {
    "build", "run", "check", "verify", "freeze", "push", "persist", "write", "decide",
    "confirm", "answer", "delete", "keep", "arm", "do", "next", "none", "done", "lock",
    "draw", "register", "harvest", "reserve", "fix", "patch", "resolve", "create",
    # irregular participles (ACTION_PAT \w+ed misses them)
    "drawn", "built", "written", "kept", "frozen", "made", "sent", "seen", "read",
    "said", "held", "ran", "went", "took", "left", "met", "cut", "got",
}
ACTION_PAT = re.compile(r"\b\w+ed\b")
DOMAIN_PAT = re.compile(r"domain\s*[:=]\s*(clinical|legal|manuscript)", re.I)
RAW_READ_PAT = re.compile(r"read (the )?raw|read lines?", re.I)
CONF_PAT = re.compile(r"\((0?\.\d+|1\.0{1,2})\)")
ID_PAT = re.compile(r"^ID\s*:\s*(\S+)", re.M)
SOURCE_PAT = re.compile(r"^SOURCE\s*:\s*(\S+)", re.M)
TOKEN_PAT = re.compile(r"^([A-Z]{1,12})(?:\s+|·|:)\s*(.*)$")
ANCHOR_WORDS = ("github.com", "commit", "pushed", "file:", "anchor", "changelog",
                "memory", "skill", "repo", "mirror", "@", "/")


def parse(text):
    regs = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if ln[0].isspace():
            if regs:
                regs[-1][1].append(s)
            continue
        m = TOKEN_PAT.match(s)
        if m:
            token, rest = m.group(1), m.group(2).strip()
            regs.append([token, [rest] if rest else []])
        else:
            regs.append(["__TEXT__", [s]])
    return regs


def lint_text(text):
    findings = []
    regs = parse(text)
    known_seq = [(i, t) for i, (t, _) in enumerate(regs) if t in KNOWN]
    for i in range(len(known_seq) - 1):
        if REGISTER_ORDER[known_seq[i][1]] > REGISTER_ORDER[known_seq[i + 1][1]]:
            findings.append("R1: register order violated (expect PROBE < I < SYSTEM < SLOT)")
            break
    for t, _ in regs:
        if t == "__TEXT__":
            findings.append("R1: unrecognized register token")
        elif t in PRE_V1_TOKENS:
            findings.append(f"R1: pre-v1 register '{t}' — historical format drift")
    probes = [b for t, b in regs if t == "PROBE"]
    if len(probes) > 3:
        findings.append(f"R2: {len(probes)} probes exceed budget 3")
    for p in probes:
        joined = " ".join(p)
        if not CONF_PAT.search(joined):
            findings.append("R2: probe missing confidence (0.XX)")
        if "basis" not in joined.lower():
            findings.append("R2: probe missing basis (or explicit 'no basis')")
    ibodies = [b for t, b in regs if t == "I"]
    icount = sum(1 + len(b) for b in ibodies)
    if icount == 0:
        findings.append("R3: I register missing")
    elif icount > 5:
        findings.append(f"R3: I register {icount} lines exceeds 5")
    if ibodies and ibodies[0] and ibodies[0][0]:
        first = ibodies[0][0]
        verbs = set(re.findall(r"[a-z]+", first.lower()))
        if not (verbs & ACTION_WORDS) and not ACTION_PAT.search(first):
            findings.append("R3: I register not action-first")
    sbodies = [b for t, b in regs if t == "SYSTEM"]
    if not sbodies:
        findings.append("R4: SYSTEM register missing")
    for b in sbodies:
        joined = " ".join(b)
        if re.search(r"\bI\b", joined) or re.search(r"\bwe\b", joined, re.I):
            findings.append("R4: first-person in SYSTEM register")
        has_anchor = any(w in joined.lower() for w in ANCHOR_WORDS) or re.search(r"\d", joined)
        if not has_anchor:
            findings.append("R4: SYSTEM line lacks anchor")
    slots = [b for t, b in regs if t == "SLOT"]
    if not slots:
        findings.append("R5: SLOT missing (null-slot must be explicit)")
    else:
        joined = " ".join(" ".join(s) for s in slots)
        if not re.search(r"none|no decision|closed|—", joined, re.I):
            findings.append("R5: SLOT unresolved (explicit null or decision required)")
    if DOMAIN_PAT.search(text) and not RAW_READ_PAT.search(text):
        findings.append("R6: high-stakes domain without raw-read instruction")
    for m in ID_PAT.finditer(text):
        if not re.fullmatch(r"[0-9a-f]{64}", m.group(1)):
            findings.append("R8: digest ID not sha256 hex")
    for m in SOURCE_PAT.finditer(text):
        p = pathlib.Path(m.group(1)).expanduser()
        in_roots = any(str(p).startswith(str(pathlib.Path(r).expanduser())) for r in ALLOWLIST_ROOTS)
        if not in_roots:
            findings.append("R8: SOURCE outside allowlist roots")
        elif not p.exists():
            findings.append("R8: SOURCE not found (orphaned digest)")
    return sorted(set(findings))


def lint_file(path):
    p = pathlib.Path(path)
    report = {"file": str(p)}
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report.update({"exit": 2, "findings": ["malformed: not UTF-8"]})
        return report
    except OSError as e:
        report.update({"exit": 2, "findings": [f"unreadable: {e}"]})
        return report
    if len(text) > MAX_CHARS or text.count("\n") > MAX_LINES:
        report.update({"exit": 2, "findings": ["malformed: size/line cap exceeded"]})
        return report
    regs = parse(text)
    register_shaped = [t for t, _ in regs if t != "__TEXT__"]
    if not register_shaped:
        report.update({"exit": 2, "findings": ["malformed: no register structure found"]})
        return report
    findings = lint_text(text)
    report.update({"exit": 1 if findings else 0, "findings": findings})
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"exit": 2, "findings": ["usage: digest_lint.py <digest.md>"]}))
        sys.exit(2)
    report = lint_file(sys.argv[1])
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    sys.exit(report["exit"])
