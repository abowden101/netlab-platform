"""Juniper vJunos-switch driver — BYO image ONLY.

LICENSE NOTICE
--------------
Juniper vJunos is proprietary software owned by Juniper Networks, Inc. This
project bundles, downloads, and links NO Juniper image, image URL, or
license key. The operator must supply their own vJunos-switch image under
their own Juniper license agreement (see docs/byo-image-guide.md). Uploads
require an explicit license acknowledgement and are verified by SHA256.

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

_DEFAULT_JUNOS_CONFIG = """\
system {
    host-name {hostname};
    login {
        user root {
            authentication {
                plain-text-password "Juniper";
            }
        }
    }
    services {
        ssh;
    }
}
"""


@register_driver
class VJunosDriver(NodeDriver):
    name = "vjunos"
    kind = "juniper_vjunos-switch"
    # BYO ONLY. Download vJunos-switch from juniper.net under your own account.
    default_image = ""
    default_credentials = Credentials(username="root", password="Juniper")
    console_method = ConsoleMethod.SSH
    boot_probe = BootProbe(
        kind="exec",
        command="show version",
        expect="JUNOS",
        timeout_s=900,
        interval_s=15,
    )

    def _require_image(self, node: NodeSpec) -> str:
        image = node.image or self.default_image
        if not image:
            raise ImageNotConfiguredError(
                "vJunos driver has no image configured. Juniper vJunos is "
                "proprietary: supply your own image under your own license "
                "via the BYO upload flow (docs/byo-image-guide.md)."
            )
        return image

    def startup_config(self, node: NodeSpec) -> str:
        self._require_image(node)
        if node.startup_config:
            return node.startup_config
        return _DEFAULT_JUNOS_CONFIG.replace("{hostname}", node.name)

    def ready(self, runner: ContainerlabRunner, node: NodeSpec) -> bool:
        return self.probe_ready(runner, node)
