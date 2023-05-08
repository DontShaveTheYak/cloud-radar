from pathlib import Path

import pytest

from cloud_radar.cf.unit._output import Output
from cloud_radar.cf.unit._stack import Stack
from cloud_radar.cf.unit._template import Template

"""Tests the functionality of the Output class."""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve(), {})


@pytest.fixture
def stack(template: Template):
    return template.create_stack({"BucketPrefix": "test"})


def test_output_constructor(stack: Stack):
    output = stack.get_output("LogsBucketName")

    assert isinstance(output, Output)

    assert output.name == "LogsBucketName"

    assert output.data == stack["Outputs"]["LogsBucketName"]

    assert output == stack["Outputs"]["LogsBucketName"]


def test_output_has_value(stack: Stack):
    output = stack.get_output("LogsBucketName")

    output.has_value()


def test_output_get_value(stack: Stack):
    output = stack.get_output("LogsBucketName")

    assert output.get_value() == stack["Outputs"]["LogsBucketName"]["Value"]


def test_output_assert_value_is(stack: Stack):
    output = stack.get_output("LogsBucketName")

    output.assert_value_is("LogsBucket")

    with pytest.raises(
        AssertionError,
        match="Output 'LogsBucketName' actual value did not match input value.",
    ):
        output.assert_value_is("test-logs-bucket2")


def test_output_has_export(stack: Stack):
    output = stack.get_output("LogsBucketName")

    output.has_export()


def test_output_get_export(stack: Stack):
    output = stack.get_output("LogsBucketName")

    assert output.get_export() == stack["Outputs"]["LogsBucketName"]["Export"]["Name"]


def test_output_assert_export_is(stack: Stack):
    output = stack.get_output("LogsBucketName")

    output.assert_export_is("test-LogsBucket")

    with pytest.raises(
        AssertionError,
        match="Output 'LogsBucketName' export value doesn't match user input.",
    ):
        output.assert_export_is("LogsBucketName2")
