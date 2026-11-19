"""netlab_drivers — pluggable NOS drivers for netlab-platform.

Importing this package registers every bundled driver. Add a vendor by
writing one driver module and importing it here.
"""

from netlab_drivers import ceos, frr, iosxe, linux, vjunos, vyos  # noqa: F401
from netlab_drivers.base import (
    DRIVERS,
    BootProbe,
    ConsoleMethod,
    ContainerlabRunner,
    Credentials,
    Lab,
    LabSession,
    NodeDriver,
    NodeSpec,
    get_driver,
    register_driver,
)

__all__ = [
    "DRIVERS",
    "BootProbe",
    "ConsoleMethod",
    "ContainerlabRunner",
    "Credentials",
    "Lab",
    "LabSession",
    "NodeDriver",
    "NodeSpec",
    "get_driver",
    "register_driver",
    "ceos",
    "frr",
    "iosxe",
    "linux",
    "vjunos",
    "vyos",
]
