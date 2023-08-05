from pathlib import Path

import pytest

from cloud_radar.cf.unit import Stack, Template


@pytest.fixture
def stack():
    template_path = Path(__file__).parent / "naming_resources.yaml"
    template = Template.from_yaml(template_path)

    # In these cases I'll usually use a non-existant region to ensure a real region
    # is not hard coded
    return template.create_stack(params={"pName": "test"}, region="xx-west-3")


def test_static_naming(stack: Stack):
    """
    This test method will check that resources in a stack, with
    substitutions resolved, match static values as expected.
    """

    # Get the bucket & check it has the expected name, based on a property
    bucket = stack.get_resource("rS3Bucket")
    bucket.assert_property_has_value("BucketName", "test-xx-west-3-bucket")

    # The EFS volume in this template also has a name including substitutions,
    # but this time the value is in a tag.
    # This resource type uses a non-standard Tag property
    efs_vol = stack.get_resource("rFileSystem")
    efs_vol.assert_tag_has_value("Name", "my-test-xx-west-3-vol", "FileSystemTags")


def test_static_naming_failure(stack: Stack):
    """
    This test method will check that resources in a stack, with
    substitutions resolved, do not match static values as expected and
    the appropriate assertion error is raised.
    """
    bucket = stack.get_resource("rS3Bucket")
    efs_vol = stack.get_resource("rFileSystem")

    with pytest.raises(
        AssertionError,
        match=(
            "Resource 'rS3Bucket' property 'BucketName' value 'test-xx-west-3-bucket'"
            " did not match input value 'not-the-bucket-name'"
        ),
    ):
        bucket.assert_property_has_value("BucketName", "not-the-bucket-name")

    with pytest.raises(
        AssertionError,
        match=(
            "Resource 'rFileSystem' tag 'Name' value 'my-test-xx-west-3-vol' "
            "did not match input value 'not-the-volume-name'"
        ),
    ):
        efs_vol.assert_tag_has_value("Name", "not-the-volume-name", "FileSystemTags")


def test_naming_pattern(stack: Stack):
    """
    This test method will check that resources in a stack, with
    substitutions resolved, match regex patterns as expected.
    """

    # Get the bucket & check it contains the region name somewhere in
    # it (a pretty common naming convention).
    bucket = stack.get_resource("rS3Bucket")
    bucket.assert_property_value_matches_pattern(
        "BucketName", r"^[a-z0-9-]*-xx-west-3[a-z0-9-]*$"
    )

    # The EFS volume in this template also has a name including substitutions,
    # but this time the value is in a tag.
    # For a pattern to match we will just check that is ends in "-vol".
    efs_vol = stack.get_resource("rFileSystem")
    # This last attribute is optional, and defaults to Tags which is used in many
    # resources.
    efs_vol.assert_tag_value_matches_pattern(
        "Name", r"^[a-z0-9-]*-vol$", "FileSystemTags"
    )
