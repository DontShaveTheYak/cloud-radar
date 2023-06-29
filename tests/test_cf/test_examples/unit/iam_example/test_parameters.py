import json
from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template


@pytest.fixture
def template():
    template_path = (
        Path(__file__).parent
        / "../../../../templates/IAM_Users_Groups_and_Policies.yaml"
    )

    return Template.from_yaml(template_path.resolve(), {})


def load_config(file_name: str) -> dict:
    config_path = Path(__file__).parent / file_name

    with config_path.open() as f:
        return json.load(f)


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
