"""Linux host driver — alpine/debian containers used as endpoints and
VLAN-aware switches in labs.

Public image, pulled automatically: ``alpine:3.20``.
"""

from __future__ import annotations

from netlab_drivers.base import (
    BootProbe,
    ConsoleMethod,
    ContainerlabRunner,
    Credentials,
    NodeDriver,
    NodeSpec,
    register_driver,
)


@register_driver
class LinuxDriver(NodeDriver):
    name = "linux"
    kind = "linux"
    default_image = "alpine:3.20"
    default_credentials = Credentials(username="root", password="")
    console_method = ConsoleMethod.SERIAL
    boot_probe = BootProbe(
        kind="exec",
        command="hostname",
        expect="",  # any output means the container answers
        timeout_s=60,
        interval_s=2,
    )
    running_config_command = "ip addr show"

    def startup_config(self, node: NodeSpec) -> str:
        """Linux hosts have no NOS config file. A caller-supplied
        startup-config is treated as a shell setup script and returned
        verbatim for the topology layer to bind-mount and execute."""
        return node.startup_config or ""

    def ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        # Empty `expect` matches any output: the probe passes as soon as
        # the container answers `hostname`.
        try:
            runner.exec(node.name, self.boot_probe.command)
            return True
        except Exception:
            return False

    def console_command(self, node: NodeSpec, container: str) -> list[str]:
        return ["docker", "exec", "-it", container, "sh"]
