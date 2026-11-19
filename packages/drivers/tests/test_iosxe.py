"""Cisco IOS-XE driver tests — BYO flow enforcement."""

import netlab_drivers.iosxe as iosxe_module
import pytest
from netlab_drivers import get_driver
from netlab_drivers.base import NodeSpec
from netlab_shared.errors import ImageNotConfiguredError

IMAGE = "byo:ios-xe-abc123"


def test_iosxe_license_notice_in_module():
    assert "LICENSE NOTICE" in iosxe_module.__doc__
    assert "bundles, downloads, and links NO Cisco image" in iosxe_module.__doc__


def test_iosxe_identity():
    driver = get_driver("ios-xe")
    assert driver.name == "ios-xe"
    assert driver.kind == "cisco_iosxe"
    assert driver.default_image == ""
    assert driver.requires_byo_image()
    assert driver.default_credentials.username == "admin"


def test_iosxe_refuses_deploy_without_image():
    driver = get_driver("ios-xe")
    node = NodeSpec(name="r1", driver="ios-xe", image="", kind="cisco_iosxe")
    with pytest.raises(ImageNotConfiguredError, match="BYO"):
        driver.startup_config(node)


def test_iosxe_startup_config_with_byo_image():
    driver = get_driver("ios-xe")
    node = NodeSpec(name="r1", driver="ios-xe", image=IMAGE, kind="cisco_iosxe")
    config = driver.startup_config(node)
    assert "hostname r1" in config
    assert "line vty" in config


def test_iosxe_ready_when_version_answers(runner):
    driver = get_driver("ios-xe")
    node = NodeSpec(name="r1", driver="ios-xe", image=IMAGE, kind="cisco_iosxe")
    runner.outputs = {"show version": "Cisco IOS XE Software, Version 17.12.01"}
    assert driver.ready(runner, node) is True


def test_iosxe_boot_probe_expects_ios_xe():
    probe = get_driver("ios-xe").boot_probe
    assert probe.expect == "Cisco IOS XE"
    assert probe.timeout_s == 900
