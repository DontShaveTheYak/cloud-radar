from pathlib import Path

import pytest

from cloud_radar.cf.unit._parameter import Parameter
from cloud_radar.cf.unit._stack import Stack
from cloud_radar.cf.unit._template import Template

"""Tests the functionality of the Parameter class."""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve(), {})


@pytest.fixture
def stack(template: Template):
    return template.create_stack({"BucketPrefix": "test"})


def test_parameter_constructor(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    assert isinstance(param, Parameter)

    assert param.name == "KeepBucket"

    assert param.data == stack["Parameters"]["KeepBucket"]


def test_parameter_has_default(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    param.has_default()

    with pytest.raises(
        AssertionError, match="Parameter 'BucketPrefix' has no default value."
    ):
        stack.get_parameter("BucketPrefix").has_default()


def test_parameter_has_no_default(stack: Stack):
    param = stack.get_parameter("BucketPrefix")

    param.has_no_default()

    with pytest.raises(
        AssertionError, match="Parameter 'KeepBucket' has a default value."
    ):
        stack.get_parameter("KeepBucket").has_no_default()


def test_parameter_default_is(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    param.assert_default_is("FALSE")

    with pytest.raises(
        AssertionError, match="Parameter 'BucketPrefix' has no default value."
    ):
        stack.get_parameter("BucketPrefix").assert_default_is("test")


def test_parameter_get_default_value(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    assert param.get_default_value() == "FALSE"

    with pytest.raises(
        AssertionError, match="Parameter 'BucketPrefix' has no default value."
    ):
        stack.get_parameter("BucketPrefix").get_default_value()


def test_parameter_has_type(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    param.has_type()


def test_parameter_type_is(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    param.assert_type_is("String")

    with pytest.raises(
        AssertionError, match="Parameter 'BucketPrefix' has type 'String'."
    ):
        stack.get_parameter("BucketPrefix").assert_type_is("List")


def test_parameter_get_type_value(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    assert param.get_type_value() == "String"


def test_parameter_has_allowed_values(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    param.has_allowed_values()

    with pytest.raises(
        AssertionError, match="Parameter 'BucketPrefix' has no allowed values."
    ):
        stack.get_parameter("BucketPrefix").has_allowed_values()


def test_parameter_allowed_values_is(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    param.assert_allowed_values_is(["TRUE", "FALSE"])

    with pytest.raises(
        AssertionError, match="Parameter 'KeepBucket' has allowed values .*"
    ):
        stack.get_parameter("KeepBucket").assert_allowed_values_is(["a", "b"])


def test_parameter_get_allowed_values(stack: Stack):
    param = stack.get_parameter("KeepBucket")

    assert param.get_allowed_values() == ["TRUE", "FALSE"]

    with pytest.raises(
        AssertionError, match="Parameter 'BucketPrefix' has no allowed values."
    ):
        stack.get_parameter("BucketPrefix").get_allowed_values()
