"""pyATS grading runner.

Runs a check command on a live node through its driver and matches the
``expect`` mapping against the output. If Genie (pyats' parser library) is
installed, the output is parsed first and the match runs against the parsed
structure; otherwise it falls back to plain text matching. Genie is an
optional dependency — the runner works without it.
"""

from __future__ import annotations

from netlab_drivers import get_driver
from netlab_drivers.base import NodeSpec

from app.grading.checks import CheckResult, match_expect
from app.labs.runner import ContainerlabRunner


def _try_genie_parse(command: str, output: str):
    """Best-effort Genie parse. Returns the parsed structure, or None when
    Genie is not installed or the command has no parser."""
    try:
        from genie.conf.base import Device  # type: ignore
        from genie.libs.parser.utils import get_parser  # type: ignore
    except ImportError:
        return None
    try:
        device = Device("netlab", os="iosxe")
        device.connect = lambda *a, **k: None  # parsing only, no connection
        parser = get_parser(command, device)
        return parser.parse(output=output)
    except Exception:
        return None


def run_pyats_check(
    runner: ContainerlabRunner,
    node_name: str,
    command: str,
    expect: dict,
    node_spec: NodeSpec | None = None,
    objective_id: str = "",
) -> CheckResult:
    """Run ``command`` on ``node_name`` and match ``expect``."""
    if node_spec is None:
        node_spec = NodeSpec(
            name=node_name,
            driver="frr",
            image="",
            kind="frr",
        )
    driver = get_driver(node_spec.driver)
    output = driver.exec(runner, node_spec, command)
    parsed = _try_genie_parse(command, output)
    if parsed is not None:
        # Match against the flattened parsed structure first; fall back to
        # text matching when the structure does not contain the value.
        import json

        flat = json.dumps(parsed, default=str)
        passed, evidence = match_expect(flat, expect)
        if passed:
            return CheckResult(objective_id, True, f"genie parse: {evidence}", "pyats")
    passed, evidence = match_expect(output, expect)
    return CheckResult(objective_id, passed, evidence, "pyats")
