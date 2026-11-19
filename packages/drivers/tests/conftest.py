"""Shared fixtures for driver tests."""

import pytest
from netlab_drivers.base import NodeSpec


class FakeRunner:
    """Stand-in for ContainerlabRunner: returns canned command output."""

    lab_name = "test-lab"

    def __init__(self, outputs=None):
        self.outputs = outputs or {}
        self.calls: list[tuple[str, str]] = []

    def exec(self, node: str, command: str, timeout_s: int = 30) -> str:
        self.calls.append((node, command))
        return self.outputs.get(command, "")

    def inspect(self, node: str) -> dict:
        return {"state": "running"}


@pytest.fixture
def runner():
    return FakeRunner()


@pytest.fixture
def frr_node():
    return NodeSpec(
        name="r1",
        driver="frr",
        image="quay.io/frrouting/frr-containerlab:10.7.1",
        kind="frr",
    )
