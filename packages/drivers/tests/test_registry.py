"""Driver registry tests."""

import pytest
from netlab_drivers import DRIVERS, get_driver
from netlab_shared.errors import UnknownDriverError

EXPECTED = {"frr", "vyos", "ceos", "vjunos", "ios-xe", "linux"}


def test_all_expected_drivers_registered():
    assert set(DRIVERS) == EXPECTED


def test_get_driver_returns_matching_instance():
    for name in EXPECTED:
        assert get_driver(name).name == name


def test_get_driver_unknown_raises():
    with pytest.raises(UnknownDriverError, match="unknown NOS driver"):
        get_driver("not-a-nos")


def test_registry_keys_match_driver_names():
    for key, cls in DRIVERS.items():
        assert cls.name == key
