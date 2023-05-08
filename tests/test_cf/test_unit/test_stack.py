from pathlib import Path

import pytest

from cloud_radar.cf.unit._stack import Stack
from cloud_radar.cf.unit._template import Template

"""Tests the functionality of the Stack class."""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve(), {})


def test_stack_constructor(template: Template):
    stack = template.create_stack({"BucketPrefix": "test"}, "us-west-2")

    assert isinstance(stack, Stack)

    assert stack == template.template

    assert stack["Parameters"] == template.template["Parameters"]

    assert stack["Metadata"]["Cloud-Radar"]["Region"] == template.Region


def test_parameters(template: Template):
    stack = template.create_stack({"BucketPrefix": "test"})

    expected_param = template.template["Parameters"]["KeepBucket"]

    actual_param = stack.get_parameter("KeepBucket")

    assert expected_param == actual_param

    stack.no_parameter("Bar")

    with pytest.raises(AssertionError, match="Parameter 'Foo' not found in template."):
        stack.get_parameter("Foo")


def test_conditions(template: Template):
    stack = template.create_stack({"BucketPrefix": "test"})

    expected_condition = template.template["Conditions"]["RetainBucket"]

    condition = stack.get_condition("RetainBucket")

    assert expected_condition == condition.get_value()

    stack.no_condition("Bar")

    with pytest.raises(AssertionError, match="Condition 'Foo' not found in template."):
        stack.get_condition("Foo")


def test_resources(template: Template):
    stack = template.create_stack({"BucketPrefix": "test"})

    expected_resource = template.template["Resources"]["LogsBucket"]

    actual_resource = stack.get_resource("LogsBucket")

    assert expected_resource == actual_resource

    stack.no_resource("Bar")

    with pytest.raises(AssertionError, match="Resource 'Foo' not found in template."):
        stack.get_resource("Foo")


def test_outputs(template: Template):
    stack = template.create_stack({"BucketPrefix": "test"})

    expected_output = template.template["Outputs"]["LogsBucketName"]

    actual_output = stack.get_output("LogsBucketName")

    assert expected_output == actual_output

    stack.no_output("Bar")

    with pytest.raises(AssertionError, match="Output 'Foo' not found in template."):
        stack.get_output("Foo")
