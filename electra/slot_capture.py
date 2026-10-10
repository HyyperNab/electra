"""slot_capture.py — SLOT closure (electra-d1).

A human decision on a digest → append-only, hash-chained ledger
(asgard/decisions.jsonl). Tamper-evident: each entry carries the hash of its
predecessor; verify() recomputes the whole chain.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sys

DEFAULT_LEDGER = pathlib.Path(__file__).resolve().parent.parent / "decisions.jsonl"


def _make(decision: str, agent: str, digest_id: str, prev: str) -> dict:
    body = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "digest_id": digest_id,
        "decision": decision,
        "agent": agent,
        "prev": prev,
    }
    body["hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode()
    ).hexdigest()[:16]
    return body


def capture(decision: str, agent: str, digest_id: str = "", ledger=DEFAULT_LEDGER) -> str:
    prev = ""
    if ledger.exists() and ledger.stat().st_size > 0:
        prev = json.loads(ledger.read_text().splitlines()[-1])["hash"]
    entry = _make(decision, agent, digest_id, prev)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry["hash"]


def verify(ledger=DEFAULT_LEDGER) -> tuple[bool, str]:
    if not ledger.exists():
        return True, "empty ledger (no entries)"
    lines = [json.loads(ln) for ln in ledger.read_text().splitlines() if ln.strip()]
    prev = ""
    for i, e in enumerate(lines):
        body = {k: v for k, v in e.items() if k != "hash"}
        recomputed = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()
        ).hexdigest()[:16]
        if recomputed != e.get("hash"):
            return False, f"entry {i}: hash mismatch"
        if body.get("prev") != prev:
            return False, f"entry {i}: chain break"
        prev = e["hash"]
    return True, f"{len(lines)} entries, chain intact"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: slot_capture.py <decision> <agent> [digest_id]", file=sys.stderr)
        sys.exit(2)
    decision, agent = sys.argv[1], sys.argv[2]
    digest_id = sys.argv[3] if len(sys.argv) > 3 else ""
    h = capture(decision, agent, digest_id)
    print(h)
