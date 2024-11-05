from pathlib import Path

import pytest

from cloud_radar.cf.unit._template import Template

"""Tests the functionality of the functions with a List type parameter."""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/test_params_list.yaml"

    return Template.from_yaml(template_path.resolve(), {})


def test_join(template: Template):
    stack = template.create_stack(
        {
            "AllowedWriters": "One,Two,Three",
            "AllowedImages": "ami-0ff8a91507f77f867,ami-0a584ac55a7631c0c",
        }
    )

    stack.get_output("JoinedWriters").assert_value_is("OneTwoThree")
    stack.get_output("JoinedImages").assert_value_is(
        "ami-0ff8a91507f77f867ami-0a584ac55a7631c0c"
    )
