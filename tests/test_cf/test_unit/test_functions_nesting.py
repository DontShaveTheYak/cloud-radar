from pathlib import Path

import pytest

from cloud_radar.cf.unit._template import Template

"""Test for bug 406 where some intrinsic functions are not supported with the right level of nesting."""


@pytest.fixture
def template():
    template_path = (
        Path(__file__).parent / "../../templates/test_functions_split_in_if.yaml"
    )

    return Template.from_yaml(template_path.resolve(), {})


def test_novalue_command(template: Template):
    stack = template.create_stack({"ContainerCommand": "", "ContainerSecretsArn": ""})

    container_def = stack.get_resource("TaskDefinition").get_property_value(
        "ContainerDefinitions"
    )
    assert container_def[0]["Command"] == ""
    assert not container_def[0]["Secrets"]


def test_value_command(template: Template):
    stack = template.create_stack({"ContainerCommand": "ls", "ContainerSecretsArn": ""})

    container_def = stack.get_resource("TaskDefinition").get_property_value(
        "ContainerDefinitions"
    )
    assert container_def[0]["Command"][0] == "ls"
    assert not container_def[0]["Secrets"]


def test_value_command_and_secret(template: Template):
    stack = template.create_stack(
        {"ContainerCommand": "ls", "ContainerSecretsArn": "arn"}
    )

    container_def = stack.get_resource("TaskDefinition").get_property_value(
        "ContainerDefinitions"
    )
    assert container_def[0]["Command"][0] == "ls"
    assert container_def[0]["Secrets"]
