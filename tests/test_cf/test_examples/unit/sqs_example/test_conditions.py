import json
from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template


@pytest.fixture
def template():
    template_path = (
        Path(__file__).parent / "../../../../templates/SQSStandardQueue.json"
    )
    with template_path.open() as f:
        template = json.load(f)
        print(template)
        return Template(template)


def test_params_create_dlq(template: Template):
    """
    This unit test case validates that when the parameter is supplied saying a DLQ
    should be created, that it is
    """
    stack = template.create_stack({"UsedeadletterQueue": "true"})

    # assert that resources have been created
    stack.has_resource("SQSQueues"), "Queue was expected to be created"
    stack.has_resource("MyDeadLetterQueue"), "DLQ was expected to be created"

    # also can assert a count of the type if that is easier


def test_params_no_create_dlq(template: Template):
    """
    This unit test case validates that when no parameter is supplied to say a DLQ
    should be created, that it is not created
    """
    stack = template.create_stack({})

    # assert that resources have been created
    stack.has_resource("SQSQueue"), "Queue was expected to be created"
    stack.no_resource("MyDeadLetterQueue"), "DLQ was expected to be created"
