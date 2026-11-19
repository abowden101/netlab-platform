#!/usr/bin/env python3
"""Validate every lab under labs/ and every Containerlab topology in the repo.

Checks:
  - lab.yml: required keys, objectives with well-formed checks
    (engine pyats|batfish, node exists in the topology, command present
    for pyats checks).
  - topology.clab.yml: valid YAML, nodes reference a known driver, links
    reference existing nodes, images are present (or explicitly BYO).

Exit code 0 when everything validates, 1 otherwise. Used by CI on every PR
that touches labs/ and by `python scripts/validate-topologies.py` locally.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

KNOWN_DRIVERS = {"frr", "vyos", "ceos", "vjunos", "ios-xe", "linux"}
# Images that are public and may be referenced directly. Anything else must
# be declared BYO (empty image + driver that requires an upload).
PUBLIC_IMAGES = {
    "quay.io/frrouting/frr-containerlab",
    "quay.io/frrouting/frr",
    "alpine",
    "debian",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_topology(path: Path, errors: list[str]) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        fail(errors, f"{path}: invalid YAML: {exc}")
        return None
    if not isinstance(data, dict):
        fail(errors, f"{path}: top level must be a mapping")
        return None
    topo = data.get("topology")
    if not isinstance(topo, dict):
        fail(errors, f"{path}: missing 'topology' mapping")
        return None
    nodes = topo.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        fail(errors, f"{path}: 'topology.nodes' must be a non-empty mapping")
        return None
    for name, node in nodes.items():
        if not isinstance(node, dict):
            fail(errors, f"{path}: node {name!r} must be a mapping")
            continue
        kind = node.get("kind")
        if kind not in KNOWN_DRIVERS:
            fail(errors, f"{path}: node {name!r} has unknown kind {kind!r}")
        image = node.get("image", "")
        if image:
            base = image.split(":")[0]
            if base not in PUBLIC_IMAGES and kind in {"frr", "linux"}:
                fail(
                    errors,
                    f"{path}: node {name!r} uses non-public image {image!r} "
                    "for a public driver — use a public image or a BYO driver",
                )
    for link in topo.get("links", []) or []:
        endpoints = link.get("endpoints", []) if isinstance(link, dict) else []
        for ep in endpoints:
            node_name = str(ep).split(":")[0]
            if node_name not in nodes:
                fail(errors, f"{path}: link endpoint {ep!r} references unknown node")
    return data


def validate_lab(path: Path, topology: dict | None, errors: list[str]) -> None:
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        fail(errors, f"{path}: invalid YAML: {exc}")
        return
    if not isinstance(data, dict):
        fail(errors, f"{path}: top level must be a mapping")
        return
    for key in ("id", "title", "topology", "objectives"):
        if key not in data:
            fail(errors, f"{path}: missing required key {key!r}")
    objectives = data.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        fail(errors, f"{path}: 'objectives' must be a non-empty list")
        return
    node_names: set[str] = set()
    if topology:
        node_names = set((topology.get("topology") or {}).get("nodes") or {})
    for obj in objectives:
        if not isinstance(obj, dict):
            fail(errors, f"{path}: objective must be a mapping")
            continue
        oid = obj.get("id", "?")
        if "title" not in obj:
            fail(errors, f"{path}: objective {oid!r} missing 'title'")
        check = obj.get("check")
        if not isinstance(check, dict):
            fail(errors, f"{path}: objective {oid!r} missing 'check' mapping")
            continue
        engine = check.get("engine")
        if engine not in {"pyats", "batfish"}:
            fail(errors, f"{path}: objective {oid!r} has unknown engine {engine!r}")
        node = check.get("node")
        if node and node_names and node not in node_names:
            fail(errors, f"{path}: objective {oid!r} references unknown node {node!r}")
        if engine == "pyats" and not check.get("command"):
            fail(errors, f"{path}: objective {oid!r} (pyats) missing 'command'")
        if engine == "batfish":
            config_file = check.get("config")
            if not config_file:
                fail(errors, f"{path}: objective {oid!r} (batfish) missing 'config'")
            elif not (path.parent / str(config_file)).exists():
                fail(
                    errors,
                    f"{path}: objective {oid!r} (batfish) config file "
                    f"{config_file!r} not found in the lab directory",
                )
        if "expect" not in check:
            fail(errors, f"{path}: objective {oid!r} missing 'expect'")


def main() -> int:
    errors: list[str] = []
    lab_dirs = sorted((ROOT / "labs").glob("*/"))
    if not lab_dirs:
        print("No labs found under labs/")
        return 1
    for lab_dir in lab_dirs:
        topo_path = lab_dir / "topology.clab.yml"
        lab_path = lab_dir / "lab.yml"
        topology = None
        if topo_path.exists():
            topology = validate_topology(topo_path, errors)
        else:
            fail(errors, f"{lab_dir}: missing topology.clab.yml")
        if lab_path.exists():
            validate_lab(lab_path, topology, errors)
        else:
            fail(errors, f"{lab_dir}: missing lab.yml")
    # Also validate any standalone topology files under packages tests fixtures.
    for extra in sorted(ROOT.glob("packages/**/fixtures/*.clab.yml")):
        validate_topology(extra, errors)
    if errors:
        print(f"Topology validation FAILED ({len(errors)} error(s)):")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"Topology validation OK ({len(lab_dirs)} lab(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
