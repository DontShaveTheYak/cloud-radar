import json
from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template


@pytest.fixture
def template():
    # This template contains a parameter for "UsedeadletterQueue", which
    # when set to true will create a second SQS queue and configure it
    # as the Dead Letter Queue for the main SQS queue this template creates.
    #
    # In this example we will use this to show a few ways to check that resource
    # conditions work as expected and different ways to perform assertions.
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
    stack.has_resource("SQSQueue"), "Queue was expected to be created"
    stack.has_resource("MyDeadLetterQueue"), "DLQ was expected to be created"

    # also can assert a count of the type if that is easier.
    # This uses the built in python filter function to only select items
    # out of the stack resources that have a type of "AWS::SQS::Queue".
    #
    # This can be modified as required in your test case to target different types,
    # or even other properties in the resource.
    sqs_resources = dict(
        filter(
            lambda item: item[1]["Type"] == "AWS::SQS::Queue",
            stack.data["Resources"].items(),
        )
    )
    assert len(sqs_resources) == 2


def test_params_no_create_dlq(template: Template):
    """
    This unit test case validates that when no parameter is supplied to say a DLQ
    should be created, that it is not created
    """

    # The parameter for "UsedeadletterQueue" defaults to false in the template,
    # so not passing any parameter values.
    stack = template.create_stack({})

    # Using the same method as above, validate we only have a single SQS queue
    # resource.
    sqs_resources = dict(
        filter(
            lambda item: item[1]["Type"] == "AWS::SQS::Queue",
            stack.data["Resources"].items(),
        )
    )
    assert len(sqs_resources) == 1

    # assert that the main queue has still been created
    stack.has_resource("SQSQueue"), "Queue was expected to be created"
    # and assert that the DLQ was not created
    stack.no_resource("MyDeadLetterQueue"), "DLQ was expected to be created"
