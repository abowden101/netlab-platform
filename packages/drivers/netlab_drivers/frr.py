"""FRR driver — FRRouting on the official Containerlab image.

Public image, pulled automatically:
    quay.io/frrouting/frr-containerlab:10.7.1

The ``-containerlab`` variant is the released FRR image with an SSH server
added (the stock image ships none). Containerlab kind is ``frr``; the
startup config is an FRR ``frr.conf`` bound into the container. Commands run
through ``vtysh -c``; the interactive console is ``docker exec <container>
vtysh``.
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

_DEFAULT_FRR_CONF = """\
frr version 10.7.1
frr defaults traditional
hostname {hostname}
log syslog informational
no ipv6 forwarding
service integrated-vtysh-config
!
line vty
!
"""


@register_driver
class FRRDriver(NodeDriver):
    name = "frr"
    kind = "frr"
    default_image = "quay.io/frrouting/frr-containerlab:10.7.1"
    # The containerlab image runs sshd; root login is used for the SSH
    # console path. The serial path (vtysh via docker exec) needs no creds.
    default_credentials = Credentials(username="root", password="frr")
    console_method = ConsoleMethod.SERIAL
    boot_probe = BootProbe(
        kind="exec",
        command='vtysh -c "show version"',
        expect="FRRouting",
        timeout_s=300,
        interval_s=5,
    )

    def startup_config(self, node: NodeSpec) -> str:
        """Return the node's FRR config. A caller-supplied startup config
        wins; otherwise render a minimal config with the node's hostname."""
        if node.startup_config:
            return node.startup_config
        return _DEFAULT_FRR_CONF.replace("{hostname}", node.name)

    def ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        return self.probe_ready(runner, node)

    def exec(self, runner: ContainerlabRunner, node: NodeSpec, command: str) -> str:
        """FRR commands go through vtysh. A bare ``show ...`` command is
        wrapped automatically; an explicit ``vtysh -c ...`` is passed as-is."""
        if command.strip().startswith("vtysh"):
            return runner.exec(node.name, command)
        return runner.exec(node.name, f'vtysh -c "{command}"')

    def console_command(self, node: NodeSpec, container: str) -> list[str]:
        return ["docker", "exec", "-it", container, "vtysh"]
