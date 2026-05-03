from pathlib import Path

import pytest

from cloud_radar.cf.unit import functions
from cloud_radar.cf.unit._template import Template

"""Tests that the LanguageExtension Length function works as expected"""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/test_length.yaml"

    return Template.from_yaml(template_path.resolve(), {})


def test_small(template: Template):
    stack = template.create_stack(
        params={"QueueNameParam": "MyQueue", "QueueList": "A,B"}
    )

    # Check the created resource has the expected property value
    queue_resource = stack.get_resource("Queue")
    queue_resource.assert_property_has_value("DelaySeconds", 2)

    # Check the condition resolved to the expected false
    stack.no_resource("QueueTwo")

    # Check the output has the expected value
    stack.get_output("QueueListLength").assert_value_is(2)


def test_direct_list_input():
    template = Template(
        {
            "Transform": "AWS::LanguageExtensions",
            "Outputs": {"ListLength": {"Value": {"Fn::Length": ["A", "B", "C"]}}},
        }
    )

    stack = template.create_stack()

    stack.get_output("ListLength").assert_value_is(3)


def test_invalid_input_type_raises():
    template = Template({})

    with pytest.raises(TypeError) as e:
        functions.length(template, "A,B")

    assert "Fn::Length - The value must be a List, not str." in str(e.value)
