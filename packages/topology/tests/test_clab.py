"""Topology package tests — load, validate, generate, lab definitions."""

from pathlib import Path

import pytest
from netlab_shared.errors import ValidationError
from netlab_topology import (
    load_lab_definition,
    load_topology,
    parse_topology,
    to_containerlab_yaml,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SAMPLE_TOPO = REPO_ROOT / "labs" / "ospf-two-router" / "topology.clab.yml"
SAMPLE_LAB = REPO_ROOT / "labs" / "ospf-two-router" / "lab.yml"


def test_load_sample_topology():
    topo = load_topology(SAMPLE_TOPO)
    assert topo.name == "ospf-two-router"
    assert set(topo.nodes) == {"r1", "r2", "sw1", "h1", "h2"}
    assert topo.nodes["r1"].kind == "frr"
    assert topo.nodes["sw1"].kind == "linux"
    assert len(topo.links) == 5
    assert topo.total_cpu() == pytest.approx(5.0)
    assert topo.total_memory_mb() == 5 * 512


def test_load_sample_lab_definition():
    lab = load_lab_definition(SAMPLE_LAB)
    assert lab.id == "ospf-two-router"
    assert len(lab.objectives) == 4
    engines = {obj.check.engine for obj in lab.objectives}
    assert engines == {"pyats", "batfish"}
    assert {obj.check.node for obj in lab.objectives} <= {"r1", "r2", "sw1"}


def test_unknown_kind_rejected():
    with pytest.raises(ValidationError, match="unknown kind"):
        parse_topology(
            {
                "name": "bad",
                "topology": {
                    "nodes": {"a": {"kind": "notanos", "image": "x:y"}},
                    "links": [],
                },
            }
        )


def test_link_to_unknown_node_rejected():
    with pytest.raises(ValidationError, match="unknown node"):
        parse_topology(
            {
                "name": "bad",
                "topology": {
                    "nodes": {"a": {"kind": "frr", "image": "quay.io/frrouting/frr:10.2.3"}},
                    "links": [{"endpoints": ["a:eth1", "ghost:eth1"]}],
                },
            }
        )


def test_public_driver_must_use_public_image():
    with pytest.raises(ValidationError, match="public image"):
        parse_topology(
            {
                "name": "bad",
                "topology": {
                    "nodes": {"a": {"kind": "frr", "image": "example.com/evil:1"}},
                    "links": [],
                },
            }
        )


def test_to_containerlab_yaml_round_trip():
    topo = load_topology(SAMPLE_TOPO)
    rendered = to_containerlab_yaml(topo)
    assert rendered["name"] == "ospf-two-router"
    assert rendered["topology"]["nodes"]["r1"]["kind"] == "frr"
    assert rendered["topology"]["nodes"]["r1"]["image"].startswith(
        "quay.io/frrouting/"
    )
    assert len(rendered["topology"]["links"]) == 5
    # The rendered mapping must itself parse cleanly.
    reparsed = parse_topology(rendered)
    assert set(reparsed.nodes) == set(topo.nodes)
