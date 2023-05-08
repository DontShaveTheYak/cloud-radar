from pathlib import Path

import pytest

from cloud_radar.cf.unit._condition import Condition
from cloud_radar.cf.unit._stack import Stack
from cloud_radar.cf.unit._template import Template

"""Tests the functionality of the Condition class."""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve(), {})


@pytest.fixture
def stack(template: Template):
    return template.create_stack({"BucketPrefix": "test"})


def test_condition_constructor(stack: Stack):
    condition = stack.get_condition("DeleteBucket")

    assert isinstance(condition, Condition)

    assert condition.name == "DeleteBucket"

    assert condition.value == stack["Conditions"]["DeleteBucket"]


def test_condition_assert_value_is(stack: Stack):
    condition = stack.get_condition("DeleteBucket")

    condition.assert_value_is(True)

    with pytest.raises(
        AssertionError, match="Condition 'DeleteBucket' is True not False."
    ):
        condition.assert_value_is(False)


def test_condition_get_value(stack: Stack):
    condition = stack.get_condition("DeleteBucket")

    assert condition.get_value() == stack["Conditions"]["DeleteBucket"]


def test_condition_eq(stack: Stack):
    condition = stack.get_condition("DeleteBucket")

    assert condition == stack["Conditions"]["DeleteBucket"]
    assert condition is not False
