from pathlib import Path

import pytest

from cloud_radar.cf.unit._resource import Resource
from cloud_radar.cf.unit._stack import Stack
from cloud_radar.cf.unit._template import Template

"""Tests the functionality of the Resource class."""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve(), {})


@pytest.fixture
def stack(template: Template):
    return template.create_stack({"BucketPrefix": "test"})


def test_resource_constructor(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    assert isinstance(resource, Resource)

    assert resource.name == "LogsBucket"

    assert resource.data == stack["Resources"]["LogsBucket"]


def test_resource_has_type(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    resource.has_type()


def test_resource_get_type_value(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    assert resource.get_type_value() == "AWS::S3::Bucket"


def test_resource_assert_type_is(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    resource.assert_type_is("AWS::S3::Bucket")

    with pytest.raises(
        AssertionError,
        match="Resource 'LogsBucket' type AWS::S3::Bucket did not match input AWS::S3::Bucket2",
    ):
        resource.assert_type_is("AWS::S3::Bucket2")


def test_resource_has_properties(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    resource.has_properties()


def test_resource_get_properties_value(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    assert (
        resource.get_properties_value()
        == stack["Resources"]["LogsBucket"]["Properties"]
    )


def test_resource_assert_propeties_is(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    resource.assert_propeties_is(stack["Resources"]["LogsBucket"]["Properties"])

    with pytest.raises(
        AssertionError,
        match="Resource 'LogsBucket' acutal properties did not match input properties",
    ):
        resource.assert_propeties_is({"test": "test"})


def test_resource_assert_has_property(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    resource.assert_has_property("BucketName")

    with pytest.raises(
        AssertionError, match="Resource 'LogsBucket' has no property BucketName2."
    ):
        resource.assert_has_property("BucketName2")


def test_resource_get_property_value(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    assert resource.get_property_value("BucketName") == "test-logs-us-east-1"

    with pytest.raises(
        AssertionError,
        match="Resource 'LogsBucket' has no property BucketName2.",
    ):
        resource.get_property_value("BucketName2")


def test_resource_assert_property_has_value(stack: Stack):
    resource = stack.get_resource("LogsBucket")

    resource.assert_property_has_value("BucketName", "test-logs-us-east-1")

    with pytest.raises(
        AssertionError,
        match="Resource 'LogsBucket' has no property BucketName2.",
    ):
        resource.assert_property_has_value("BucketName2", "test-logs-us-east-1")

    with pytest.raises(
        AssertionError,
        match=(
            "Resource 'LogsBucket' property 'BucketName' value"
            " 'test-logs-us-east-1' did not match input value 'test-logs-us-east-12'."
        ),
    ):
        resource.assert_property_has_value("BucketName", "test-logs-us-east-12")
