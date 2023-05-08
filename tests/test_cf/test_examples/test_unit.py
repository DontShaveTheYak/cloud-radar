from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve(), {})


def test_log_defaults(template: Template):
    stack = template.create_stack({"BucketPrefix": "testing"})

    stack.has_resource("LogsBucket")

    stack.no_resource("RetainLogsBucket")

    bucket = stack.get_resource("LogsBucket")

    bucket_name = bucket.get_property_value("BucketName")

    assert "us-east-1" in bucket_name


def test_log_retain(template: Template):
    stack = template.create_stack(
        {"BucketPrefix": "testing", "KeepBucket": "TRUE"}, region="us-west-2"
    )

    stack.no_resource("LogsBucket")

    bucket = stack.get_resource("RetainLogsBucket")

    assert "DeletionPolicy" in bucket

    assert bucket["DeletionPolicy"] == "Retain"

    bucket_name = bucket.get_property_value("BucketName")

    assert "us-west-2" in bucket_name

    always_true = stack.get_condition("AlwaysTrue")

    always_true.assert_value_is(True)
