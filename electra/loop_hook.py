"""loop_hook.py — pipeline-end hook (electra-d1).

spec.json → generated digest → linted. Subprocess boundary to digest_lint.py
(no cross-tree import; the generator never re-implements lint rules).
Exit codes propagate: 0 clean · 1 flags · 2 malformed.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))  # direct-script invocation support

from electra.digest_gen import generate


def run(spec_path: str, out_path: str) -> int:
    spec = json.load(open(spec_path))
    digest = generate(spec)
    pathlib.Path(out_path).write_text(digest, encoding="utf-8")
    lint = pathlib.Path(__file__).resolve().parent / "digest_lint.py"
    r = subprocess.run(
        [sys.executable, str(lint), out_path], capture_output=True, text=True
    )
    sys.stdout.write(r.stdout)
    if r.stderr:
        sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: loop_hook.py <spec.json> <out.digest.md>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run(sys.argv[1], sys.argv[2]))
