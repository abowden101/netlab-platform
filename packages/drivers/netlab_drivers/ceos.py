"""Arista cEOS driver — BYO image ONLY.

LICENSE NOTICE
--------------
Arista cEOS is proprietary software owned by Arista Networks, Inc. This
project bundles, downloads, and links NO Arista image, image URL, or license
key. The operator must supply their own cEOS image under their own Arista
license agreement (see docs/byo-image-guide.md). Uploads require an explicit
license acknowledgement and are verified by SHA256.

    default_image = ""  (BYO only)
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

_DEFAULT_EOS_CONFIG = """\
hostname {hostname}
!
username admin privilege 15 secret admin
!
management api http-commands
   no shutdown
!
interface Management1
   no shutdown
!
end
"""


@register_driver
class CEOSDriver(NodeDriver):
    name = "ceos"
    kind = "ceos"
    # BYO ONLY. Download cEOS from arista.com under your own account.
    default_image = ""
    default_credentials = Credentials(username="admin", password="admin")
    console_method = ConsoleMethod.SSH
    boot_probe = BootProbe(
        kind="exec",
        command="show version",
        expect="Arista",
        timeout_s=600,
        interval_s=10,
    )

    def _require_image(self, node: NodeSpec) -> str:
        image = node.image or self.default_image
        if not image:
            raise ImageNotConfiguredError(
                "cEOS driver has no image configured. Arista cEOS is "
                "proprietary: supply your own image under your own license "
                "via the BYO upload flow (docs/byo-image-guide.md)."
            )
        return image

    def startup_config(self, node: NodeSpec) -> str:
        self._require_image(node)
        if node.startup_config:
            return node.startup_config
        return _DEFAULT_EOS_CONFIG.replace("{hostname}", node.name)

    def ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        return self.probe_ready(runner, node)
