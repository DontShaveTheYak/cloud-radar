import json
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

    return Template.from_yaml(template_path.resolve(), {})


def test_default_values(template: Template):
    # The template used in this example includes default values, this will show
    # that these are valid, and that values can be substituted in.

    stack = template.create_stack()

    # No error at this point means that validation rules have
    # passed, go on to check the resource properties to see the value
    # has been substituted
    table_resource = stack.get_resource("MyTable")

    # Assert that the SSM parameter is resolved based on our dynamic reference
    # lookup.
    database_name_value = table_resource.get_property_value("DatabaseName")

    assert database_name_value == "my-test-database"


def test_invalid_ssm_pattern(template: Template):
    with pytest.raises(
        ValueError,
        match=r"Value .* does not match the expected pattern for SSM parameter MyBucket",
    ):
        template.create_stack(params={"MyBucket": "bad-ssm-path-$*£&@*"})


def test_ssm_key_without_reference():
    print("TODO")


def test_unsupported_ssm_parameter_type():
    print("TODO")
