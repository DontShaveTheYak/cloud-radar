from pathlib import Path

import pytest

from cloud_radar.cf.e2e._stack import Stack, _create_tc_config


@pytest.fixture(scope="session")
def template_dir():
    return Path(__file__).parent / "../../templates"


@pytest.fixture()
def default_params():
    parameters = {
        "BucketPrefix": "taskcat-$[taskcat_random-string]",
        "KeepBucket": "FALSE",
    }

    return parameters


def test_constructor(template_dir, default_params):
    template = template_dir / "log_bucket" / "log_bucket.yaml"

    stack = Stack(template)

    assert stack.config.config.project.regions[0] == "us-east-1"

    assert stack.config.config.project.parameters is None

    stack = Stack(str(template))

    default_params["KeepBucket"] = "TRUE"

    stack = Stack(template, parameters=default_params)

    test = stack.config.config.tests["default"]

    assert test.parameters == default_params

    regions = ["us-west-1"]

    stack = Stack(template, regions=regions)

    assert stack.config.config.project.regions == regions


def test_tc_config():
    # We have to go a second level down
    # because it looks two levels up for the function
    # name to avoid the init function
    def inner_func():
        return _create_tc_config()

    config = inner_func()

    assert config["project"]["name"] == "taskcat-test-tc-config"
    assert config["tests"]["default"] == {}
