"""Live-network tests (marker acceptance) run only with --run-acceptance."""

import pytest


def pytest_addoption(parser):
    parser.addoption("--run-acceptance", action="store_true", default=False,
                     help="run the live-network acceptance tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-acceptance"):
        return
    skip = pytest.mark.skip(reason="live network: pass --run-acceptance to run")
    for item in items:
        if "acceptance" in item.keywords:
            item.add_marker(skip)
