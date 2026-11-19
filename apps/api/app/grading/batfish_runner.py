"""Batfish-style grading runner — offline config analysis.

Batfish itself is a JVM tool; this runner implements the two analyses the
sample labs need directly in Python, over the node's startup-config text:

- ``vlans``: the VLAN ids that must exist in the config.
- ``isolated``: no single port may be a member of two of the listed VLANs.

It parses ``bridge vlan add dev <dev> vid <n>`` lines (Linux bridge
config, as used by sw1) and Cisco-style ``switchport access vlan <n>`` /
``switchport trunk allowed vlan <list>`` lines. If the config format is
unrecognised, the check fails with an explicit evidence string rather than
passing silently.
"""

from __future__ import annotations

import re
from pathlib import Path

from netlab_topology import LabDefinition

from app.core.config import settings
from app.grading.checks import CheckResult

_BRIDGE_VLAN_RE = re.compile(
    r"bridge vlan add dev (\S+) vid (\d+)", re.IGNORECASE
)
_ACCESS_VLAN_RE = re.compile(
    r"switchport access vlan (\d+)", re.IGNORECASE
)
_TRUNK_VLAN_RE = re.compile(
    r"switchport trunk allowed vlan ([\d,]+)", re.IGNORECASE
)


def _parse_vlan_membership(config_text: str) -> dict[str, set[int]]:
    """Return {port: {vlan ids}} from config text."""
    membership: dict[str, set[int]] = {}
    for match in _BRIDGE_VLAN_RE.finditer(config_text):
        port, vid = match.group(1), int(match.group(2))
        membership.setdefault(port, set()).add(vid)
    # Cisco-style: track the current interface block.
    current_interface: str | None = None
    for line in config_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("interface "):
            current_interface = stripped.split(None, 1)[1]
            continue
        if current_interface is None:
            continue
        access = _ACCESS_VLAN_RE.search(stripped)
        if access:
            membership.setdefault(current_interface, set()).add(int(access.group(1)))
        trunk = _TRUNK_VLAN_RE.search(stripped)
        if trunk:
            for vid in trunk.group(1).split(","):
                if vid.strip():
                    membership.setdefault(current_interface, set()).add(int(vid))
    return membership


def run_batfish_check(
    lab: LabDefinition,
    node: str,
    expect: dict,
    config_file: str | None = None,
    objective_id: str = "",
) -> CheckResult:
    """Analyse the node's startup-config file for VLAN expectations."""
    if not config_file:
        return CheckResult(objective_id, False, "batfish check needs a 'config' file", "batfish")
    config_path = Path(settings.labs_dir) / lab.id / config_file
    if not config_path.exists():
        return CheckResult(
            objective_id, False, f"config file {config_file!r} not found in lab {lab.id!r}", "batfish"
        )
    config_text = config_path.read_text()
    membership = _parse_vlan_membership(config_text)
    evidence: list[str] = []
    vlans = expect.get("vlans")
    if vlans is not None:
        present = set()
        for vids in membership.values():
            present |= vids
        missing = [v for v in vlans if v not in present]
        evidence.append(f"vlans present: {sorted(present)}")
        if missing:
            evidence.append(f"missing vlans: {missing}")
            return CheckResult(objective_id, False, "; ".join(evidence), "batfish")
    if expect.get("isolated") and vlans is not None:
        wanted = set(vlans)
        for port, vids in membership.items():
            shared = vids & wanted
            if len(shared) > 1:
                evidence.append(f"port {port} carries {sorted(shared)} — not isolated")
                return CheckResult(objective_id, False, "; ".join(evidence), "batfish")
        evidence.append("no port carries two of the listed VLANs")
    return CheckResult(objective_id, True, "; ".join(evidence), "batfish")
