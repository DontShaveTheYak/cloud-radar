import pytest  # noqa: F401


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: Run tests that deploy resources on AWS.")
