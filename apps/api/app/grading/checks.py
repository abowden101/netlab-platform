"""Shared grading primitives: check results and expect-matching.

Kept in its own module so the engine and the per-engine runners can both
import it without a circular dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CheckResult:
    objective_id: str
    passed: bool
    evidence: str
    engine: str


def match_expect(output: str, expect: dict) -> tuple[bool, str]:
    """Match an ``expect`` mapping against command output.

    - ``contains``: substring must appear.
    - ``regex``: pattern must match.
    - any other key: the *value* must appear in the output (e.g.
      ``state: FULL`` checks the output contains ``FULL``).
    """
    evidence: list[str] = []
    for key, value in expect.items():
        if key == "contains":
            ok = str(value) in output
            evidence.append(f"contains {value!r}: {'yes' if ok else 'no'}")
            if not ok:
                return False, "; ".join(evidence)
        elif key == "regex":
            ok = re.search(str(value), output) is not None
            evidence.append(f"regex {value!r}: {'match' if ok else 'no match'}")
            if not ok:
                return False, "; ".join(evidence)
        else:
            ok = str(value) in output
            evidence.append(f"{key}={value!r}: {'found' if ok else 'missing'}")
            if not ok:
                return False, "; ".join(evidence)
    return True, "; ".join(evidence) if evidence else "no expectations"
