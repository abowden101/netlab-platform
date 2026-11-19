"""FRR driver tests — the reference driver."""

from netlab_drivers import get_driver
from netlab_drivers.base import ConsoleMethod, NodeSpec


def test_frr_identity():
    driver = get_driver("frr")
    assert driver.name == "frr"
    assert driver.kind == "frr"
    assert driver.default_image == "quay.io/frrouting/frr-containerlab:10.7.1"
    assert driver.console_method is ConsoleMethod.SERIAL
    assert driver.default_credentials.username == "root"


def test_frr_boot_probe():
    probe = get_driver("frr").boot_probe
    assert probe.kind == "exec"
    assert probe.command == 'vtysh -c "show version"'
    assert probe.expect == "FRRouting"
    assert probe.timeout_s == 300


def test_frr_default_startup_config_has_hostname():
    driver = get_driver("frr")
    node = NodeSpec(name="r1", driver="frr", image=driver.default_image, kind="frr")
    config = driver.startup_config(node)
    assert "hostname r1" in config
    assert "service integrated-vtysh-config" in config


def test_frr_custom_startup_config_passes_through():
    driver = get_driver("frr")
    custom = "hostname r1\nrouter ospf\n"
    node = NodeSpec(
        name="r1",
        driver="frr",
        image=driver.default_image,
        kind="frr",
        startup_config=custom,
    )
    assert driver.startup_config(node) == custom


def test_frr_exec_wraps_in_vtysh(runner):
    driver = get_driver("frr")
    node = NodeSpec(name="r1", driver="frr", image=driver.default_image, kind="frr")
    driver.exec(runner, node, "show ip ospf neighbor")
    assert runner.calls == [
        ("r1", 'vtysh -c "show ip ospf neighbor"'),
    ]


def test_frr_exec_passes_explicit_vtysh_through(runner):
    driver = get_driver("frr")
    node = NodeSpec(name="r1", driver="frr", image=driver.default_image, kind="frr")
    driver.exec(runner, node, 'vtysh -c "show version"')
    assert runner.calls == [("r1", 'vtysh -c "show version"')]


def test_frr_ready_when_version_answers(runner):
    driver = get_driver("frr")
    node = NodeSpec(name="r1", driver="frr", image=driver.default_image, kind="frr")
    runner.outputs = {
        'vtysh -c "show version"': "Hello, this is FRRouting (version 10.7.1)."
    }
    assert driver.ready(runner, node) is True


def test_frr_console_command_is_vtysh():
    driver = get_driver("frr")
    node = NodeSpec(name="r1", driver="frr", image=driver.default_image, kind="frr")
    assert driver.console_command(node, "clab-test-r1") == [
        "docker",
        "exec",
        "-it",
        "clab-test-r1",
        "vtysh",
    ]
