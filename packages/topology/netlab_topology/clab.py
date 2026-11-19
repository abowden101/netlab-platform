"""Containerlab topology loading, validation, and generation.

A topology is the declarative core of a lab: nodes (each bound to a NOS
driver), links, and per-node resources. This package is the single place
that knows the Containerlab YAML shape — the API and the CLI validator both
go through here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from netlab_shared.errors import ValidationError

KNOWN_KINDS = {"frr", "vyos", "ceos", "vjunos", "ios-xe", "linux"}

# Images that may be referenced directly because they are public.
PUBLIC_IMAGE_PREFIXES = (
    "quay.io/frrouting/",
    "alpine:",
    "debian:",
)


@dataclass
class TopologyNode:
    name: str
    kind: str
    image: str = ""
    startup_config: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    cpu_limit: float = 1.0
    memory_limit_mb: int = 512

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.kind not in KNOWN_KINDS:
            errors.append(f"node {self.name!r}: unknown kind {self.kind!r}")
        if self.kind in {"frr", "linux"} and self.image:
            if not any(
                self.image.startswith(prefix) for prefix in PUBLIC_IMAGE_PREFIXES
            ):
                errors.append(
                    f"node {self.name!r}: public driver {self.kind!r} must use "
                    f"a public image, got {self.image!r}"
                )
        if self.cpu_limit <= 0:
            errors.append(f"node {self.name!r}: cpu_limit must be > 0")
        if self.memory_limit_mb <= 0:
            errors.append(f"node {self.name!r}: memory_limit_mb must be > 0")
        return errors


@dataclass
class TopologyLink:
    endpoints: tuple[str, str]

    def validate(self, node_names: set[str]) -> list[str]:
        errors: list[str] = []
        for ep in self.endpoints:
            if ":" not in ep:
                errors.append(f"link endpoint {ep!r} must be 'node:interface'")
                continue
            node_name = ep.split(":", 1)[0]
            if node_name not in node_names:
                errors.append(f"link endpoint {ep!r} references unknown node")
        return errors


@dataclass
class LabTopology:
    name: str
    nodes: dict[str, TopologyNode] = field(default_factory=dict)
    links: list[TopologyLink] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("topology must have a name")
        if not self.nodes:
            errors.append("topology must declare at least one node")
        for node in self.nodes.values():
            errors.extend(node.validate())
        for link in self.links:
            errors.extend(link.validate(set(self.nodes)))
        return errors

    def total_cpu(self) -> float:
        return sum(node.cpu_limit for node in self.nodes.values())

    def total_memory_mb(self) -> int:
        return sum(node.memory_limit_mb for node in self.nodes.values())


def load_topology(path: str | Path) -> LabTopology:
    """Load a Containerlab YAML file into a LabTopology. Raises
    ValidationError on bad YAML or a failed validation."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValidationError(f"{path}: invalid YAML: {exc}") from exc
    return parse_topology(data, source=str(path))


def _parse_memory(value: Any) -> int:
    """Parse a memory value: int MB, or a string like "512M"."""
    if isinstance(value, str):
        return int(value.strip().rstrip("Mm"))
    return int(value)


def parse_topology(data: dict[str, Any], source: str = "<dict>") -> LabTopology:
    """Parse an already-loaded mapping into a LabTopology."""
    if not isinstance(data, dict):
        raise ValidationError(f"{source}: top level must be a mapping")
    topo = data.get("topology")
    if not isinstance(topo, dict):
        raise ValidationError(f"{source}: missing 'topology' mapping")
    nodes: dict[str, TopologyNode] = {}
    raw_nodes = topo.get("nodes")
    if not isinstance(raw_nodes, dict) or not raw_nodes:
        raise ValidationError(f"{source}: 'topology.nodes' must be a non-empty mapping")
    for node_name, raw in raw_nodes.items():
        if not isinstance(raw, dict):
            raise ValidationError(f"{source}: node {node_name!r} must be a mapping")
        nodes[node_name] = TopologyNode(
            name=node_name,
            kind=str(raw.get("kind", "")),
            image=str(raw.get("image", "") or ""),
            startup_config=raw.get("startup-config"),
            env=dict(raw.get("env") or {}),
            cpu_limit=float(raw.get("cpu", 1.0) or 1.0),
            memory_limit_mb=_parse_memory(raw.get("memory", 512) or 512),
        )
    links: list[TopologyLink] = []
    for raw_link in topo.get("links", []) or []:
        endpoints = raw_link.get("endpoints", []) if isinstance(raw_link, dict) else []
        if len(endpoints) == 2:
            links.append(TopologyLink(endpoints=(str(endpoints[0]), str(endpoints[1]))))
    topology = LabTopology(name=str(data.get("name", "")), nodes=nodes, links=links)
    errors = topology.validate()
    if errors:
        raise ValidationError(f"{source}: " + "; ".join(errors))
    return topology


def to_containerlab_yaml(topology: LabTopology) -> dict[str, Any]:
    """Render a LabTopology back to a Containerlab YAML mapping. The API
    writes this to a temp file and hands it to `containerlab deploy`."""
    nodes: dict[str, Any] = {}
    for node in topology.nodes.values():
        entry: dict[str, Any] = {"kind": node.kind}
        if node.image:
            entry["image"] = node.image
        if node.startup_config:
            entry["startup-config"] = node.startup_config
        if node.env:
            entry["env"] = node.env
        entry["cpu"] = node.cpu_limit
        entry["memory"] = f"{node.memory_limit_mb}M"
        nodes[node.name] = entry
    return {
        "name": topology.name,
        "topology": {
            "nodes": nodes,
            "links": [
                {"endpoints": list(link.endpoints)} for link in topology.links
            ],
        },
    }


@dataclass
class ObjectiveCheck:
    engine: str  # "pyats" | "batfish"
    node: str
    command: str = ""
    config: str = ""  # batfish: config file inside the lab dir to analyse
    expect: dict[str, Any] = field(default_factory=dict)


@dataclass
class LabObjective:
    id: str
    title: str
    check: ObjectiveCheck
    description: str = ""


@dataclass
class LabDefinition:
    id: str
    title: str
    topology_file: str
    objectives: list[LabObjective] = field(default_factory=list)
    description: str = ""
    estimated_minutes: int = 45


def load_lab_definition(path: str | Path) -> LabDefinition:
    """Load and validate a lab.yml coursework file."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValidationError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: top level must be a mapping")
    errors: list[str] = []
    for key in ("id", "title", "topology", "objectives"):
        if key not in data:
            errors.append(f"missing required key {key!r}")
    objectives: list[LabObjective] = []
    for raw in data.get("objectives") or []:
        if not isinstance(raw, dict):
            errors.append("objective must be a mapping")
            continue
        check = raw.get("check") or {}
        if check.get("engine") not in {"pyats", "batfish"}:
            errors.append(
                f"objective {raw.get('id', '?')!r}: unknown engine {check.get('engine')!r}"
            )
        if check.get("engine") == "pyats" and not check.get("command"):
            errors.append(f"objective {raw.get('id', '?')!r}: pyats check needs 'command'")
        if "expect" not in check:
            errors.append(f"objective {raw.get('id', '?')!r}: check needs 'expect'")
        objectives.append(
            LabObjective(
                id=str(raw.get("id", "")),
                title=str(raw.get("title", "")),
                description=str(raw.get("description", "") or ""),
                check=ObjectiveCheck(
                    engine=str(check.get("engine", "")),
                    node=str(check.get("node", "")),
                    command=str(check.get("command", "") or ""),
                    config=str(check.get("config", "") or ""),
                    expect=dict(check.get("expect") or {}),
                ),
            )
        )
    if errors:
        raise ValidationError(f"{path}: " + "; ".join(errors))
    return LabDefinition(
        id=str(data["id"]),
        title=str(data["title"]),
        topology_file=str(data["topology"]),
        objectives=objectives,
        description=str(data.get("description", "") or ""),
        estimated_minutes=int(data.get("estimated_minutes", 45) or 45),
    )
