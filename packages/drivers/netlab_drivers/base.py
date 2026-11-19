"""Pluggable NOS driver interface.

Every network OS in netlab-platform is a driver. The orchestrator only ever
talks to this interface; adding a vendor means adding one file plus one
registry line — nothing else changes.

Each driver defines the five attributes from the platform spec:
  - image name (``default_image``; empty means BYO — see iosxe.py)
  - default credentials
  - boot-ready probe
  - console method
  - startup-config template (via ``startup_config``)

Console command note: ``console_command`` takes the resolved container name
because Containerlab names containers ``clab-<lab>-<node>`` and only the
session layer knows the lab name. The proposal sketch showed a one-argument
form; the two-argument form is the realization of that stub.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class ConsoleMethod(StrEnum):
    SSH = "ssh"        # console over SSH (cEOS, vJunos, VyOS)
    SERIAL = "serial"  # console via `docker exec` (IOS-XE, FRR)
    TELNET = "telnet"  # legacy fallback


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str
    enable_password: str | None = None   # IOS enable secret


@dataclass(frozen=True)
class BootProbe:
    """How the backend knows a node is ready for a console."""

    kind: str          # "ssh" | "exec" | "tcp"
    command: str       # e.g. "show version"; "" for a bare TCP connect
    expect: str        # substring that must appear in output
    timeout_s: int = 300
    interval_s: int = 5


@dataclass
class NodeSpec:
    name: str
    driver: str              # registry key, e.g. "frr"
    image: str               # resolved container image ref
    kind: str                # containerlab node kind
    startup_config: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    cpu_limit: float = 1.0
    memory_limit_mb: int = 512


class ContainerlabRunner(Protocol):
    """Lab-bound runner. The orchestrator builds one per deployed lab, so
    drivers never need to know the lab name — only the node name."""

    lab_name: str

    def exec(self, node: str, command: str, timeout_s: int = 30) -> str:
        """Run a command on a node and return its stdout."""
        ...

    def inspect(self, node: str) -> dict:
        """Return containerlab inspect data for a node."""
        ...


@dataclass
class Lab:
    """A deployed lab session as the orchestrator sees it."""

    id: str
    slug: str
    clab_name: str
    nodes: list[str]
    status: str = "deploying"


class NodeDriver(ABC):
    """One driver per NOS. All five spec'd attributes live here."""

    name: str                                  # "frr" | "vyos" | "ceos" | "vjunos" | "ios-xe" | "linux"
    kind: str                                  # containerlab kind, e.g. "linux", "ceos"
    default_image: str                         # e.g. "quay.io/frrouting/frr-containerlab:10.7.1"
    default_credentials: Credentials
    console_method: ConsoleMethod
    boot_probe: BootProbe
    # Command that returns the running config (used by the default snapshot).
    running_config_command: str = "show running-config"

    @abstractmethod
    def startup_config(self, node: NodeSpec) -> str:
        """Render the node's startup config from template + node vars."""

    @abstractmethod
    def ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        """Run the boot probe; True when the node accepts a console."""

    def exec(self, runner: ContainerlabRunner, node: NodeSpec, command: str) -> str:
        """Run a command on the node. Override when the NOS needs a wrapper
        (e.g. FRR commands go through ``vtysh -c``)."""
        return runner.exec(node.name, command)

    def console_command(self, node: NodeSpec, container: str) -> list[str]:
        """Command the console proxy spawns for an interactive session.
        Override per NOS; the default is an SSH console."""
        creds = self.default_credentials
        return [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{creds.username}@{container}",
        ]

    def snapshot(self, runner: ContainerlabRunner, node: NodeSpec) -> str:
        """Capture the node's running config."""
        return self.exec(runner, node, self.running_config_command)

    # -- shared helpers -------------------------------------------------

    def probe_ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        """Run ``boot_probe`` until it succeeds or times out."""
        probe = self.boot_probe
        deadline = time.monotonic() + probe.timeout_s
        while True:
            try:
                if probe.kind in ("exec", "ssh"):
                    output = self.exec(runner, node, probe.command)
                else:  # "tcp": a bare connect is enough; exec returns "" on success
                    output = runner.exec(node.name, "")
                if probe.expect in output:
                    return True
            except Exception:
                pass
            if time.monotonic() >= deadline:
                return False
            time.sleep(probe.interval_s)

    def requires_byo_image(self) -> bool:
        """True when the driver ships no default image (licensed NOS)."""
        return not self.default_image


# -- registry -----------------------------------------------------------

DRIVERS: dict[str, type[NodeDriver]] = {}   # populated by netlab_drivers.__init__


def register_driver(cls: type[NodeDriver]) -> type[NodeDriver]:
    """Class decorator: ``@register_driver`` on a driver registers it."""
    DRIVERS[cls.name] = cls
    return cls


def get_driver(name: str) -> NodeDriver:
    """Return an instance of the driver registered under ``name``."""
    from netlab_shared.errors import UnknownDriverError

    try:
        return DRIVERS[name]()
    except KeyError as exc:
        raise UnknownDriverError(
            f"unknown NOS driver {name!r}; registered drivers: {sorted(DRIVERS)}"
        ) from exc


class LabSession(ABC):
    """Orchestrator seam (implemented in apps/api/app/labs/manager.py).
    Shown here so drivers and the API share one vocabulary."""

    @abstractmethod
    def deploy(self, topology: dict) -> Lab: ...

    @abstractmethod
    def destroy(self, lab_id: str) -> None: ...

    @abstractmethod
    def snapshot(self, lab_id: str) -> str: ...

    @abstractmethod
    def reset(self, lab_id: str) -> None: ...

    @abstractmethod
    def console_stream(self, lab_id: str, node: str) -> None: ...  # WebSocket
