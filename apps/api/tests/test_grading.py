"""Grading engine tests — pure logic, no Docker needed."""

from pathlib import Path

from app.grading.batfish_runner import run_batfish_check
from app.grading.checks import match_expect
from app.grading.pyats_runner import run_pyats_check
from netlab_topology import load_lab_definition

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SAMPLE_LAB = REPO_ROOT / "labs" / "ospf-two-router" / "lab.yml"


class FakeRunner:
    def exec(self, node, command, timeout_s=30):
        return (
            "Neighbor ID     Pri   State           Dead Time   Address\n"
            "2.2.2.2         1     FULL/DR         00:00:39    10.0.12.2\n"
        )

    def inspect(self, node):
        return {}


def test_match_expect_contains():
    passed, _ = match_expect("hello world", {"contains": "world"})
    assert passed
    passed, _ = match_expect("hello world", {"contains": "missing"})
    assert not passed


def test_match_expect_regex():
    passed, _ = match_expect("FULL/DR  00:00:39", {"regex": r"FULL/\w+"})
    assert passed
    passed, _ = match_expect("state INIT", {"regex": r"FULL/\w+"})
    assert not passed


def test_match_expect_state_value():
    passed, _ = match_expect("FULL/DR", {"state": "FULL"})
    assert passed


def test_pyats_check_passes_on_real_output():
    result = run_pyats_check(
        FakeRunner(), "r1", "show ip ospf neighbor", {"state": "FULL"}
    )
    assert result.passed is True
    assert result.engine == "pyats"


def test_pyats_check_fails_on_missing_state():
    result = run_pyats_check(
        FakeRunner(), "r1", "show ip ospf neighbor", {"state": "FULL/BDR"}
    )
    assert result.passed is False


def test_batfish_vlan_isolation_passes():
    lab = load_lab_definition(SAMPLE_LAB)
    result = run_batfish_check(
        lab, "sw1", {"vlans": [10, 20], "isolated": True}, config_file="sw1-setup.sh"
    )
    assert result.passed is True
    assert "no port carries two" in result.evidence


def test_batfish_missing_vlan_fails():
    lab = load_lab_definition(SAMPLE_LAB)
    result = run_batfish_check(
        lab, "sw1", {"vlans": [10, 99], "isolated": True}, config_file="sw1-setup.sh"
    )
    assert result.passed is False
    assert "missing vlans" in result.evidence


def test_batfish_missing_config_file_fails():
    lab = load_lab_definition(SAMPLE_LAB)
    result = run_batfish_check(
        lab, "sw1", {"vlans": [10, 20]}, config_file="no-such-file.sh"
    )
    assert result.passed is False
