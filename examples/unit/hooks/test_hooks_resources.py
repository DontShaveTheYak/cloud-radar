from pathlib import Path

import pytest

from cloud_radar.cf.unit import Resource, Stack, Template


def my_s3_naming_hook(
    resource_data: Resource, stack_info: Stack, template_info: Template
) -> None:
    name: str = resource_data.get_property_value("BucketName")

    assert (
        template_info.Region in name
    ), "All buckets are expected to include the region in their name"


def my_s3_encryption_hook(resource_data, stack_info, template_info: Template) -> None:
    assert (
        resource_data.get_property_value("BucketEncryption") is True
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
