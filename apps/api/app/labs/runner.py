"""Runners: how the API talks to Containerlab (primary) and plain Docker
(fallback). Both implement the ``ContainerlabRunner`` protocol the drivers
consume, so the driver layer never sees which one is in use.

ContainerlabRunner is the real path: `containerlab deploy/destroy/exec/
inspect` against a generated topology file. DockerRunner is the fallback
for hosts without Containerlab: it renders the topology to a Compose file
(one service per node, one shared network) and drives it with
`docker compose`. The fallback gives L2 connectivity but NOT per-link
topology fidelity — point-to-point links are a Containerlab feature.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import yaml
from netlab_shared.errors import RunnerError
from netlab_topology import LabTopology, to_containerlab_yaml


def _run(cmd: list[str], timeout_s: int = 120) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_s
        )
    except FileNotFoundError as exc:
        raise RunnerError(
            f"command not found: {cmd[0]} — is it installed on the lab host?"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(f"command timed out: {' '.join(cmd)}") from exc


class ContainerlabRunner:
    """Primary runner: shells out to the `containerlab` binary."""

    def __init__(
        self,
        lab_name: str,
        topology_file: str | Path,
        binary: str = "containerlab",
    ):
        self.lab_name = lab_name
        self.topology_file = str(topology_file)
        self.binary = binary

    def deploy(self) -> None:
        # --disable-rp-filter: containerlab tries to write
        # /proc/sys/net/ipv4/conf/all/rp_filter on the Docker host. On
        # Docker Desktop that path is read-only from inside a container,
        # so the deploy fails before any node starts. Skipping it is safe
        # for symmetric lab traffic (OSPF adjacencies, loopback routes).
        result = _run(
            [self.binary, "deploy", "--disable-rp-filter", "-t", self.topology_file],
            timeout_s=600,
        )
        if result.returncode != 0:
            raise RunnerError(
                f"containerlab deploy failed: {result.stderr.strip()}"
            )

    def destroy(self) -> None:
        result = _run(
            [self.binary, "destroy", "-t", self.topology_file, "--cleanup"],
            timeout_s=300,
        )
        if result.returncode != 0:
            raise RunnerError(
                f"containerlab destroy failed: {result.stderr.strip()}"
            )

    def exec(self, node: str, command: str, timeout_s: int = 30) -> str:
        result = _run(
            [
                self.binary,
                "exec",
                "-t",
                self.topology_file,
                "--node",
                node,
                "--cmd",
                command,
            ],
            timeout_s=timeout_s,
        )
        if result.returncode != 0:
            raise RunnerError(
                f"exec on {node!r} failed: {result.stderr.strip()}"
            )
        return result.stdout

    def inspect(self, node: str) -> dict:
        result = _run(
            [
                self.binary,
                "inspect",
                "--lab",
                self.lab_name,
                "--format",
                "json",
            ],
            timeout_s=30,
        )
        if result.returncode != 0:
            raise RunnerError(
                f"containerlab inspect failed: {result.stderr.strip()}"
            )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RunnerError("containerlab inspect returned bad JSON") from exc
        containers = data.get("containers", [])
        for entry in containers:
            if entry.get("name") in (node, f"clab-{self.lab_name}-{node}"):
                return entry
        return {}

    @staticmethod
    def container_name(lab_name: str, node: str) -> str:
        return f"clab-{lab_name}-{node}"


class DockerRunner:
    """Fallback runner: plain Docker via a generated Compose file.

    Honest limitation: Compose gives one shared L2 network, not the
    point-to-point links a Containerlab topology declares. Labs that depend
    on exact link topology must run on Containerlab.
    """

    def __init__(self, lab_name: str, topology: LabTopology):
        self.lab_name = lab_name
        self.topology = topology
        self._compose_file: Path | None = None

    @staticmethod
    def container_name(lab_name: str, node: str) -> str:
        return f"clab-{lab_name}-{node}"

    def _write_compose(self) -> Path:
        services: dict = {}
        for node in self.topology.nodes.values():
            services[node.name] = {
                "image": node.image,
                "container_name": self.container_name(self.lab_name, node.name),
                "networks": [self.lab_name],
                "privileged": True,
                "deploy": {
                    "resources": {
                        "limits": {
                            "cpus": str(node.cpu_limit),
                            "memory": f"{node.memory_limit_mb}M",
                        }
                    }
                },
            }
        compose = {
            "name": self.lab_name,
            "services": services,
            "networks": {self.lab_name: {"driver": "bridge"}},
        }
        tmp = Path(tempfile.mkdtemp(prefix=f"netlab-{self.lab_name}-"))
        compose_file = tmp / "docker-compose.yml"
        compose_file.write_text(yaml.safe_dump(compose))
        self._compose_file = compose_file
        return compose_file

    def deploy(self) -> None:
        compose_file = self._write_compose()
        result = _run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            timeout_s=600,
        )
        if result.returncode != 0:
            raise RunnerError(f"docker compose up failed: {result.stderr.strip()}")

    def destroy(self) -> None:
        if self._compose_file is None:
            return
        result = _run(
            ["docker", "compose", "-f", str(self._compose_file), "down"],
            timeout_s=300,
        )
        if result.returncode != 0:
            raise RunnerError(
                f"docker compose down failed: {result.stderr.strip()}"
            )

    def exec(self, node: str, command: str, timeout_s: int = 30) -> str:
        result = _run(
            [
                "docker",
                "exec",
                self.container_name(self.lab_name, node),
                "sh",
                "-c",
                command,
            ],
            timeout_s=timeout_s,
        )
        if result.returncode != 0:
            raise RunnerError(
                f"docker exec on {node!r} failed: {result.stderr.strip()}"
            )
        return result.stdout

    def inspect(self, node: str) -> dict:
        result = _run(
            ["docker", "inspect", self.container_name(self.lab_name, node)],
            timeout_s=30,
        )
        if result.returncode != 0:
            return {}
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}
        return data[0] if data else {}


def render_topology_file(topology: LabTopology, directory: str | Path) -> Path:
    """Write a Containerlab YAML file for a topology. Returns the path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "topology.clab.yml"
    path.write_text(yaml.safe_dump(to_containerlab_yaml(topology)))
    return path
