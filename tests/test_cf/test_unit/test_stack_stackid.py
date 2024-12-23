# Test case that verifies that generation of the value for AWS::StackId works as expected

from pathlib import Path

import pytest

from cloud_radar.cf.unit._template import Template


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/test_stackid.yaml"

    return Template.from_yaml(template_path.resolve(), {})


def test_function_populated_var(template):
    expected_value = "arn:aws:cloudformation:us-west-2:123456789012:stack/teststack/51af3dc0-da77-11e4-872e-1234567db123"
    Template.StackId = expected_value

    actual_value = template._get_populated_stack_id()
    assert actual_value == expected_value


def test_function_blank_var(template):
    Template.StackId = ""

    actual_value = template._get_populated_stack_id()
    # Check all except the UUID
    assert actual_value.startswith(
        f"arn:{Template.Partition}:cloudformation:{Template.Region}:{Template.AccountId}:stack/{Template.StackName}/"
    )

    # Check the UUID part looks UUID like
    unique_uuid = actual_value.split("/")[2]
    assert 5 == len(unique_uuid.split("-"))


def test_template_blank_var_stack_region(template):
    Template.StackId = ""

    stack = template.create_stack({}, region="eu-west-1")

    bucket = stack.get_resource("UniqueBucket")
    bucket_name = bucket.get_property_value("BucketName")

    assert len(bucket_name) == 37
    assert bucket_name[:18] == "my-test-eu-west-1-"
    assert bucket_name[30:] == "-bucket"


def test_template_blank_var_global_region(template):
    Template.StackId = ""

    stack = template.create_stack({})

    bucket = stack.get_resource("UniqueBucket")
    bucket_name = bucket.get_property_value("BucketName")

    assert len(bucket_name) == 37
    assert bucket_name[:18] == "my-test-us-east-1-"
    assert bucket_name[30:] == "-bucket"


def test_template_populated_var(template):
    Template.StackId = "arn:aws:cloudformation:us-west-2:123456789012:stack/teststack/51af3dc0-da77-11e4-872e-1234567db123"

    stack = template.create_stack({})

    bucket = stack.get_resource("UniqueBucket")
    bucket_name = bucket.get_property_value("BucketName")

    assert "my-test-us-west-2-1234567db123-bucket" == bucket_name
