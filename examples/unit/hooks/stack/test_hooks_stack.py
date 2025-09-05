from pathlib import Path
from typing import List

import pytest

from cloud_radar.cf.unit import StackHookContext, Template


@pytest.fixture()
def configure_hooks():
    # Add in locally defined template level hooks
    Template.Hooks.stack = [my_output_check]

    yield

    # Clear the hooks after
    Template.Hooks.stack = []


# Example hook that checks that no output has a value longer than 25 characters
def my_output_check(context: StackHookContext) -> None:

    # Get all the outputs
    outputs = context.stack.data["Outputs"]
    for output_name in outputs:
        output = context.stack.get_output(output_name)

        output_value = output.get_value()
        print(f"Output value: {output_value}")

        # Check the lengths
        if len(output_value) >= 25:
            raise ValueError(
                (
                    f"{output_name} - All outputs are expected to have a "
                    "value less than 25 characters"
                )
            )


# Helper method to load a template file relative to this test file
def load_template(filename: str):
    template_path = Path(__file__).parent / filename
    template = Template.from_yaml(template_path)

    return template


# Test case showing that when all hooks pass, no errors are raised.
@pytest.mark.usefixtures("configure_hooks")
def test_basic_all_success():
    # Loading the template will validate the template
    # level hooks
    template = load_template("stack_naming_resources.yaml")

    # Render the stack, this will execute the stack level hooks
    template.create_stack(params={"pName": "test"}, region="xx-west-3")


# Test case showing that when a stack hook causes an error,
# we see it at the point of loading the stack
@pytest.mark.usefixtures("configure_hooks")
def test_basic_failure():

    template = load_template("stack_naming_resources.yaml")

    # Rendering the stack will cause the failure
    with pytest.raises(
        ValueError,
        match="oBucket - All outputs are expected to have a "
        "value less than 25 characters",
    ):
        # Render the stack, this will execute the stack level hooks
        template.create_stack(
            params={"pName": "test-really-long-name"}, region="xx-west-3"
        )
