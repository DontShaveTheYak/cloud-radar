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


def test_naming_conventions(stack: Stack):
    """
    This test shows how common naming conventions can be checked across all
    resources in a stack, including ignoring resource types which do not support
    names.

    Args:
            stack (Stack): the stack being used for these test examples
    """

    # Ideally this dict would be coming from a common library
    # function that you have shared between all your test cases
    # (assuming consistency is the goal).
    #
    # This defines all the resource types we want to check, the pattern to match,
    # and either the details of the Tag or Property that the name is held in.
    known_naming_conventions = {
        "AWS::EFS::FileSystem": {
            "Tag": "Name",
            # This TagProperty is optional. The default is 'Tags',
            # but some resources use a different property name for
            # their tags.
            "TagProperty": "FileSystemTags",
            "Pattern": r"^[a-z0-9-]*-vol$",
        },
        "AWS::S3::Bucket": {
            "Property": "BucketName",
            "Pattern": r"^[a-z0-9-]*-xx-west-3[a-z0-9-]*$",
        },
        "AWS::S3::BucketPolicy": {
            # The BucketPolicy type does not support custom names. If we do not
            # want to set fail_on_missing_type=False when we call the assertion
            # below then we need to include this type in the dict, and set it
            # not to be checked.
            # This approach ensures that types do not slip through unintentionally.
            "Check": False
        },
    }

    stack.assert_resource_type_property_value_conventions(known_naming_conventions)


def test_missing_convention(stack: Stack):
    """
    This test shows how the fail_on_missing_type parameter on
    assert_resource_type_property_value_conventions can be used to
    error or ignore types without a convention defined.

    Args:
            stack (Stack): the stack being used for these test examples
    """

    # There is an optional parameter that can be used to ignore a resource being found
    # that does not have a convention set for it.
    # With this set, if we supplied a dict without any entries then no assertion error
    # would be raised.
    stack.assert_resource_type_property_value_conventions(
        type_patterns={}, fail_on_missing_type=False
    )

    # The default behaviour is for fail_on_missing_type to be set to True,
    # resulting in an assertion error
    with pytest.raises(
        AssertionError,
        match=(
            "Resource 'rFileSystem' has type 'AWS::EFS::FileSystem' "
            "which is not included in the supplied type_patterns."
        ),
    ):
        stack.assert_resource_type_property_value_conventions(type_patterns={})
