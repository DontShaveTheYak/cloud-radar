from pathlib import Path

import pytest

from cloud_radar.cf.unit import ResourceHookContext, Template

# TODO: Docs - Hook names should be descriptive and unique


# Example hook that verifies that the rendered bucket name (after
# substitutions) includes the region the template is being deployed to.
def my_s3_naming_hook(context: ResourceHookContext) -> None:
    name: str = context.resource_definition.get_property_value("BucketName")

    if context.template.Region not in name:
        raise ValueError(
            (
                f"{context.logical_id} - All buckets are "
                "expected to include the region in their name"
            )
        )


# Example hook that verifies  that all S3 bucket definitions
# have the "BucketEncryption" property set
def my_s3_encryption_hook(context: ResourceHookContext) -> None:
    # Use one of the built in functions to confirm the property exists
    context.resource_definition.assert_has_property("BucketEncryption")


# Helper method to load a template file relative to this test file
# and set the resource level hooks.
def load_template(filename: str):
    template_path = Path(__file__).parent / filename
    template = Template.from_yaml(template_path)

    # Add in locally defined hooks
    template.hooks.resources = {
        "AWS::S3::Bucket": [my_s3_naming_hook, my_s3_encryption_hook]
    }

    return template


# Test case showing that when all hooks pass, no errors are raised.
def test_basic_all_success():
    template = load_template("naming_resources.yaml")

    # In these cases I'll usually use a non-existant region to ensure a real region
    # is not hard coded

    # Render the stack, this will execute the resource level hooks
    template.create_stack(params={"pName": "test"}, region="xx-west-3")


# Test case showing that when a resource hook causes an error,
# we see it at the point of creating the rendered stack
def test_basic_resource_failure():
    template = load_template("naming_resources_no_encryption.yaml")

    # Render the stack, this will execute the resource level hooks
    with pytest.raises(
        AssertionError, match="Resource 'rS3Bucket' has no property BucketEncryption."
    ):
        template.create_stack(params={"pName": "test"}, region="xx-west-3")


# The contents of this test template are mostly the same as the one we used for
# test_basic_resource_failure, but this time we have the appropriate Metadata
# at the Template level to ignore the resource hook that was failing
def test_template_suppression_success():
    template = load_template("naming_resources_no_encryption_template_suppression.yaml")

    template.create_stack(params={"pName": "test"}, region="xx-west-3")


# This test is similar to test_template_suppression_success,
# but shows that if the hook being ignored is different from the
# failing one that we still see the failure.
def test_template_suppression_diff_hook():
    template = load_template(
        "naming_resources_no_encryption_template_suppression_diff_rule.yaml"
    )

    with pytest.raises(
        AssertionError, match="Resource 'rS3Bucket' has no property BucketEncryption."
    ):
        template.create_stack(params={"pName": "test"}, region="xx-west-3")


# The contents of this test template are mostly the same as the one we used for
# test_basic_resource_failure, but this time we have the appropriate Metadata
# at the Resource level to ignore the resource hook that was failing
def test_resource_suppression_success():
    template = load_template(
        "naming_resources_no_encryption_resource_suppression_diff_rule.yaml"
    )

    with pytest.raises(
        AssertionError, match="Resource 'rS3Bucket' has no property BucketEncryption."
    ):
        template.create_stack(params={"pName": "test"}, region="xx-west-3")
