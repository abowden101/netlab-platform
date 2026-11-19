"""VyOS driver.

There is NO official prebuilt VyOS router container image. VyOS LTS package
repositories are closed to the public; only rolling nightly ISOs are
published. The runtime image must be built by the operator from a nightly
ISO — see ``scripts/build-vyos-image.sh`` — and then configured here.

    default_image = ""  (BYO-built; set ``vyos-runtime:<version>``)

Deploying a VyOS node without a configured image raises
``ImageNotConfiguredError`` with instructions. Nothing is downloaded by
this driver.
"""

from __future__ import annotations

from netlab_shared.errors import ImageNotConfiguredError

from netlab_drivers.base import (
    BootProbe,
    ConsoleMethod,
    ContainerlabRunner,
    Credentials,
    NodeDriver,
    NodeSpec,
    register_driver,
)

_DEFAULT_VYOS_CONFIG = """\
set system host-name {hostname}
set system login user vyos authentication plaintext-password 'vyos'
set service ssh port 22
"""


@register_driver
class VyOSDriver(NodeDriver):
    name = "vyos"
    kind = "vyos"
    # No public prebuilt image exists. Build one with
    # scripts/build-vyos-image.sh and set image to vyos-runtime:<version>.
    default_image = ""
    default_credentials = Credentials(username="vyos", password="vyos")
    console_method = ConsoleMethod.SSH
    boot_probe = BootProbe(
        kind="exec",
        command="show version",
        expect="VyOS",
        timeout_s=600,
        interval_s=10,
    )

    def _require_image(self, node: NodeSpec) -> str:
        image = node.image or self.default_image
        if not image:
            raise ImageNotConfiguredError(
                "VyOS driver has no image configured. Build a runtime image "
                "with scripts/build-vyos-image.sh <version> and set the "
                "node image to vyos-runtime:<version>."
            )
        return image

    def startup_config(self, node: NodeSpec) -> str:
        """Return the node's VyOS config in ``set`` form. A caller-supplied
        startup config wins; otherwise render a minimal config with the
        node's hostname."""
        self._require_image(node)
        if node.startup_config:
            return node.startup_config
        return _DEFAULT_VYOS_CONFIG.replace("{hostname}", node.name)

    def ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        return self.probe_ready(runner, node)

    def exec(self, runner: ContainerlabRunner, node: NodeSpec, command: str) -> str:
        """VyOS operational commands go through the op-mode wrapper when run
        inside the container; an explicit wrapper call is passed as-is."""
        if command.strip().startswith("/opt/vyatta/bin/vyatta-op-cmd-wrapper"):
            return runner.exec(node.name, command)
        return runner.exec(
            node.name, f"/opt/vyatta/bin/vyatta-op-cmd-wrapper {command}"
        )
