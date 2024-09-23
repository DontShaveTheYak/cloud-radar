from pathlib import Path

import pytest

from cloud_radar.cf.unit._template import Template

"""Tests the functionality of the functions with a CommaDelimitedList parameter."""


@pytest.fixture
def template():
    template_path = (
        Path(__file__).parent / "../../templates/test_params_commadelimited.yaml"
    )

    return Template.from_yaml(template_path.resolve(), {})


def test_join(template: Template):
    stack = template.create_stack({"AllowedWriters": "One,Two,Three"})

    stack.get_output("Joined").assert_value_is("OneTwoThree")
