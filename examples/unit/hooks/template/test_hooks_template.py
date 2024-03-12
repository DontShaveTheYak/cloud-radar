from pathlib import Path
from typing import List

import pytest

from cloud_radar.cf.unit import ResourceHookContext, Template


@pytest.fixture()
def configure_hooks():
    # Add in locally defined template level hooks
    Template.Hooks.template = [my_parameter_prefix_checks]

    yield

    # Clear the hooks after
    Template.Hooks.template = []


def _object_prefix_check(items: List[str], expected_prefix: str):
    # Iterate through each parameter checking them
    for item in items:
        if not item.startswith(expected_prefix):
            raise ValueError(
                f"{item} does not follow the convention of starting with '{expected_prefix}'"
            )


# Example hook that checks that the cloudformation template
# name for all parameters starts with a "p".
def my_parameter_prefix_checks(template: Template) -> None:
    # Get all the parameters
    parameters = template.template.get("Parameters", {})

    # Check them
    _object_prefix_check(parameters, "p")


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
    load_template("naming_resources.yaml")


# Test case showing that when a template hook causes an error,
# we see it at the point of loading the template
@pytest.mark.usefixtures("configure_hooks")
def test_basic_failure():
    # Loading the template will cause the failure
    with pytest.raises(
        ValueError, match="Name does not follow the convention of starting with 'p'"
    ):
        load_template("naming_resources_failure.yaml")
