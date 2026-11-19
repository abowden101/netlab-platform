"""VyOS driver tests — proves the abstraction holds for a second driver
and that the BYO-build image flow is enforced."""

import pytest
from netlab_drivers import get_driver
from netlab_drivers.base import NodeSpec
from netlab_shared.errors import ImageNotConfiguredError

IMAGE = "vyos-runtime:1.5-rolling-202507120000"


def test_vyos_identity():
    driver = get_driver("vyos")
    assert driver.name == "vyos"
    assert driver.kind == "vyos"
    assert driver.default_image == ""  # no official prebuilt image exists
    assert driver.requires_byo_image()


def test_vyos_startup_config_renders_set_commands():
    driver = get_driver("vyos")
    node = NodeSpec(name="r1", driver="vyos", image=IMAGE, kind="vyos")
    config = driver.startup_config(node)
    assert "set system host-name r1" in config
    assert "set service ssh" in config


def test_vyos_exec_wraps_in_op_wrapper(runner):
    driver = get_driver("vyos")
    node = NodeSpec(name="r1", driver="vyos", image=IMAGE, kind="vyos")
    driver.exec(runner, node, "show interfaces")
    assert runner.calls == [
        ("r1", "/opt/vyatta/bin/vyatta-op-cmd-wrapper show interfaces"),
    ]


def test_vyos_ready_when_version_answers(runner):
    driver = get_driver("vyos")
    node = NodeSpec(name="r1", driver="vyos", image=IMAGE, kind="vyos")
    runner.outputs = {
        "/opt/vyatta/bin/vyatta-op-cmd-wrapper show version": "VyOS 1.5-rolling"
    }
    assert driver.ready(runner, node) is True


def test_vyos_error_names_the_build_script():
    driver = get_driver("vyos")
    node = NodeSpec(name="r1", driver="vyos", image="", kind="vyos")
    with pytest.raises(ImageNotConfiguredError, match="build-vyos-image"):
        driver.startup_config(node)
