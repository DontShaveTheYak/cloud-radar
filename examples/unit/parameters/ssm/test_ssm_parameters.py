from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template


@pytest.fixture
def template():
    # This template contains a single parameter for "Password", which
    # is constrained to be a string with a minimum length of 1 character,
    # and a maximum of 41 characters.
    #
    # In this example we will use this to show a few ways to check that parameter
    # validation works as expected and different ways to perform assertions.
    #
    # This example also uses CodePipeline like CloudFormation parameter files
    # to show how you can validate this type of parameter file as part of
    # your unit tests.
    template_path = Path(__file__).parent / "SSM_Parameter_example.yaml"

    return Template.from_yaml(
        template_path.resolve(),
        dynamic_references={
            "ssm": {
                "/my_parameters/database/name": "my-great-database",
                "/product/dev/eu-west-1/import/assets-bucket": "my-great-s3-bucket",
                "/product/dev/eu-west-2/import/assets-bucket": "my-greatest-s3-bucket",
            }
        },
    )


def test_default_values(template: Template):
    # The template used in this example includes default values, this will show
    # that these are valid, and that values can be substituted in.

    stack = template.create_stack()

    # No error at this point means that validation rules have
    # passed, go on to check the resource properties to see the value
    # has been substituted
    table_resource = stack.get_resource("MyTable")

    # Assert that the SSM parameter used in a Ref is resolved based on our
    # dynamic reference lookup.
    database_name_value = table_resource.get_property_value("DatabaseName")

    assert database_name_value == "my-great-database"

    table_input = table_resource.get_property_value("TableInput")

    # Assert that the SSM parameter used as part of a dynamic reference
    # is resolved
    table_input_name = table_input["Name"]
    assert table_input_name == "my-great-database_my_table"

    # Assert that the SSM parameter used in a Sub is resolved based on the
    # lookup
    location = table_input["StorageDescriptor"]["Location"]
    assert location == "s3://my-great-s3-bucket/test"


def test_invalid_ssm_pattern(template: Template):
    with pytest.raises(
        ValueError,
        match=r"Value .* does not match the expected pattern for SSM parameter MyBucket",
    ):
        template.create_stack(params={"MyBucket": "bad-ssm-path-$*£&@*"})


def test_ssm_key_without_reference(template: Template):
    """
    This test case covers where an SSM parameter key is supplied but isn't referenced
    in the template definition
    """
    with pytest.raises(
        KeyError,
        match=(
            "Key /an/ssm/key/that/does/not/exist not included "
            "in dynamic references configuration for service ssm"
        ),
    ):
        template.create_stack(params={"MyBucket": "/an/ssm/key/that/does/not/exist"})


def test_unsupported_ssm_parameter_type():
    """
    This test case covers if an SSM parameter is defined in the template which uses an unknown
    value type (really this should be caught by a linter first)
    """

    template = Template(
        template={
            "Parameters": {
                "MyBucket": {
                    "Type": "AWS::SSM::Parameter::Value<NotARealType>",
                    "Description": "The bucket name where all the data will be put into.",
                }
            }
        }
    )

    with pytest.raises(
        ValueError,
        match="Type NotARealType is not a supported SSM value type for  SSM parameter MyBucket",
    ):
        template.create_stack(params={"MyBucket": "/an/ssm/key/that/does/not/exist"})


def test_supplied_value(template: Template):
    # Test showing that when an SSM parameter key is supplied as a parameter,
    # the correct substitution is performed.

    stack = template.create_stack(
        params={"MyBucket": "/product/dev/eu-west-2/import/assets-bucket"}
    )

    # No error at this point means that validation rules have
    # passed, go on to check the resource properties to see the value
    # has been substituted
    table_resource = stack.get_resource("MyTable")

    # Assert that the SSM parameter used in a Sub is resolved based on the
    # lookup
    table_input = table_resource.get_property_value("TableInput")
    location = table_input["StorageDescriptor"]["Location"]
    assert location == "s3://my-greatest-s3-bucket/test"
