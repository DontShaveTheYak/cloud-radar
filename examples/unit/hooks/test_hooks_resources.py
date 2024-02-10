from pathlib import Path

import pytest

from cloud_radar.cf.unit import ResourceHookContext, Template

# TODO: Docs - Hook names should be descriptive and unique


def my_s3_naming_hook(context: ResourceHookContext) -> None:
    name: str = context.resource_definition.get_property_value("BucketName")

    assert (
        context.template.Region in name
    ), f"{context.logical_id} - All buckets are expected to include the region in their name"


def my_s3_encryption_hook(context: ResourceHookContext) -> None:
    assert (
        context.resource_definition.get_property_value("BucketEncryption") is True
    ), "All buckets are expected to have encryption enabled"


# Template.hooks = {
#     "AWS::S3::Bucket": [my_s3_naming_hook, my_s3_encryption_hook]
# }


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "naming_resources.yaml"
    template = Template.from_yaml(template_path)

    # Add in locally defined hooks
    template.hooks.resources = {
        "AWS::S3::Bucket": [my_s3_naming_hook, my_s3_encryption_hook]
    }

    return template


def test_basic_load(template):
    # In these cases I'll usually use a non-existant region to ensure a real region
    # is not hard coded
    with pytest.raises(AssertionError):
        template.create_stack(params={"pName": "test"}, region="xx-west-3")
