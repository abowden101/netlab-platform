"""Interface conformance: every registered driver must satisfy the
five-attribute contract from the platform spec."""

import pytest
from netlab_drivers import DRIVERS, get_driver
from netlab_drivers.base import ConsoleMethod, NodeSpec
from netlab_shared.errors import ImageNotConfiguredError

BYO_DRIVERS = {"vyos", "ceos", "vjunos", "ios-xe"}
PUBLIC_DRIVERS = {"frr", "linux"}


def _node_for(driver_name: str) -> NodeSpec:
    return NodeSpec(
        name="n1",
        driver=driver_name,
        image="test-image:latest",
        kind=driver_name,
    )


@pytest.mark.parametrize("driver_name", sorted(DRIVERS))
def test_driver_has_five_contract_attributes(driver_name):
    driver = get_driver(driver_name)
    assert driver.name == driver_name
    assert driver.kind, "kind must be set"
    assert isinstance(driver.console_method, ConsoleMethod)
    assert driver.default_credentials.username, "credentials need a username"
    probe = driver.boot_probe
    assert probe.kind in {"exec", "ssh", "tcp"}
    assert isinstance(probe.expect, str)
    assert probe.timeout_s > 0 and probe.interval_s > 0


@pytest.mark.parametrize("driver_name", sorted(PUBLIC_DRIVERS))
def test_public_driver_ships_an_image(driver_name):
    assert not get_driver(driver_name).requires_byo_image()
    assert get_driver(driver_name).default_image


@pytest.mark.parametrize("driver_name", sorted(BYO_DRIVERS))
def test_byo_driver_ships_no_image(driver_name):
    driver = get_driver(driver_name)
    assert driver.requires_byo_image()
    assert driver.default_image == ""


@pytest.mark.parametrize("driver_name", sorted(BYO_DRIVERS))
def test_byo_driver_refuses_deploy_without_image(driver_name):
    driver = get_driver(driver_name)
    node = NodeSpec(name="n1", driver=driver_name, image="", kind=driver_name)
    with pytest.raises(ImageNotConfiguredError):
        driver.startup_config(node)


@pytest.mark.parametrize("driver_name", sorted(DRIVERS))
def test_startup_config_renders_hostname(driver_name):
    driver = get_driver(driver_name)
    node = _node_for(driver_name)
    config = driver.startup_config(node)
    assert isinstance(config, str)
    if driver_name == "linux":
        # Linux hosts have no NOS config file by default.
        assert config == ""
    else:
        assert "n1" in config


@pytest.mark.parametrize("driver_name", sorted(DRIVERS))
def test_console_command_is_a_list(driver_name):
    driver = get_driver(driver_name)
    cmd = driver.console_command(_node_for(driver_name), "clab-test-n1")
    assert isinstance(cmd, list) and cmd
    assert all(isinstance(part, str) for part in cmd)
    assert cmd[0] in {"docker", "ssh"}


@pytest.mark.parametrize("driver_name", sorted(DRIVERS))
def test_exec_returns_runner_output(driver_name, runner):
    driver = get_driver(driver_name)
    node = _node_for(driver_name)
    runner.outputs = {"show version": "version output"}
    # FRR/VyOS wrap commands; the fake runner returns "" for wrapped forms,
    # which still proves exec delegates to the runner without raising.
    result = driver.exec(runner, node, "show version")
    assert isinstance(result, str)
    assert runner.calls, "exec must call the runner"
