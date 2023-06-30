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
    template_path = (
        Path(__file__).parent
        / "../../../../templates/IAM_Users_Groups_and_Policies.yaml"
    )

    return Template.from_yaml(template_path.resolve(), {})


def load_config(file_name: str) -> dict:
    """
    Loads a json configuration file into a dict.

    :param file_name: the name of the configuration file to load, relative to the
                      location of this test file
    """
    config_path = Path(__file__).parent / file_name

    with config_path.open() as f:
        return json.load(f)


def read_params_codepipeline_format(config: dict) -> dict:
    return config["Parameters"]


# def read_params_

# def convert_params_cloudformation_format


def test_valid_params(template: Template):
    config = load_config("valid_params.json")

    stack = template.create_stack(config["Parameters"])

    # No error at this point means that validation rules have
    # passed, go on to check the resource properties
    user_resource = stack.get_resource("CFNUser")
    login_profile_props = user_resource.get_property_value("LoginProfile")
    assert login_profile_props["Password"] == "aSuperSecurePassword"


def test_invalid_params(template: Template):
    config = load_config("invalid_params.json")

    with pytest.raises(
        ValueError,
        match=(
            "Value abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXZY is longer "
            "than the maximum length for parameter Password"
        ),
    ):
        template.create_stack(config["Parameters"])
