import json
import re
from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template

known_naming_conventions = {
    "AWS::SQS::Queue": {
        "NameField": "QueueName",
        "NamingConvention": r"^[a-z0-9-]*-queue$",
    }
}


def get_name_value(resource: dict, name_path: str):
    full_path = "Properties." + name_path

    current_value = resource
    for path_part in full_path.split("."):
        current_value = current_value.get(path_part)
        if path_part is None:
            return None

    return current_value


def pytest_generate_tests(metafunc):
    """
    This test case takes advantage of the pytest generator functionality
    to dynamically parameterise the test based on the number of resources
    that we have in our template.

    Without this, we would implement a test that looped through the resources
    and performed assertions for each one. This would result in a test failure
    when one resource did not match the naming convention, it would not test
    all resources
    """

    # Load the template
    template_path = (
        Path(__file__).parent / "../../../../templates/SQSStandardQueue.json"
    )
    with template_path.open() as f:
        template = Template(json.load(f))

    # Render the template
    stack = template.create_stack({"UsedeadletterQueue": "true"})

    metafunc.parametrize(
        "resource_name, resource_value", stack.data["Resources"].items()
    )


def test_naming(resource_name: str, resource_value: dict):
    naming_convention = known_naming_conventions.get(resource_value.get("Type"))
    if naming_convention is not None:
        # Get the name of the resource
        name = get_name_value(resource_value, naming_convention["NameField"])

        assert name is not None, "Name value not found in resource"

        # Compare the name against the naming convention regex
        assert re.match(
            naming_convention["NamingConvention"], name
        ), "Name does not match convention regex"
