"""Cisco IOS-XE driver — BYO image ONLY.

LICENSE NOTICE
--------------
Cisco IOS-XE is proprietary software owned by Cisco Systems, Inc. This
project bundles, downloads, and links NO Cisco image, image URL, or license
key. The operator must supply their own IOS-XE container image under their
own Cisco license agreement (see docs/byo-image-guide.md). Uploading an
image requires an explicit license acknowledgement, and the upload is
verified by SHA256 before it can be used.

    default_image = ""  (BYO only — there is no public default)

Deploying an IOS-XE node without a configured image raises
``ImageNotConfiguredError``. The driver never attempts to download anything.
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

_DEFAULT_IOSXE_CONFIG = """\
hostname {hostname}
!
username admin privilege 15 secret admin
!
ip domain-name lab.local
!
line vty 0 4
 login local
 transport input ssh
!
end
"""


@register_driver
class IOSXEDriver(NodeDriver):
    name = "ios-xe"
    kind = "cisco_iosxe"
    # BYO ONLY. There is no public or default image. See docs/byo-image-guide.md.
    default_image = ""
    # Documented lab defaults for the Catalyst 8000V container. Change them
    # in the topology before any shared deployment.
    default_credentials = Credentials(
        username="admin", password="admin", enable_password="admin"
    )
    console_method = ConsoleMethod.SSH
    boot_probe = BootProbe(
        kind="exec",
        command="show version",
        expect="Cisco IOS XE",
        timeout_s=900,
        interval_s=15,
    )

    def _require_image(self, node: NodeSpec) -> str:
        image = node.image or self.default_image
        if not image:
            raise ImageNotConfiguredError(
                "IOS-XE driver has no image configured. Cisco IOS-XE is "
                "proprietary: supply your own image under your own license "
                "via the BYO upload flow (docs/byo-image-guide.md) and set "
                "the node image to the uploaded image reference."
            )
        return image

    def startup_config(self, node: NodeSpec) -> str:
        """Return the node's IOS-XE startup config. A caller-supplied
        startup config wins; otherwise render a minimal config with the
        node's hostname."""
        self._require_image(node)
        if node.startup_config:
            return node.startup_config
        return _DEFAULT_IOSXE_CONFIG.replace("{hostname}", node.name)

    def ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        return self.probe_ready(runner, node)

    def console_command(self, node: NodeSpec, container: str) -> list[str]:
        # IOS-XE container console over SSH to the container.
        creds = self.default_credentials
        return [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{creds.username}@{container}",
        ]
