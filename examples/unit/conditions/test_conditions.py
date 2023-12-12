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
    template_path = Path(__file__).parent / "SQSStandardQueue.json"
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

    # You also can assert a count of the type if that is easier.
    sqs_resources = stack.get_resources_of_type("AWS::SQS::Queue")
    assert len(sqs_resources) == 2

    # When the second queue is being created, the SQSQueue should have a
    # redrive policy set referring to it
    main_queue = stack.get_resource("SQSQueue")
    redrive_policy = main_queue.get_property_value("RedrivePolicy")
    assert redrive_policy.get("deadLetterTargetArn") == "MyDeadLetterQueue.Arn"


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
    sqs_resources = stack.get_resources_of_type("AWS::SQS::Queue")
    assert len(sqs_resources) == 1

    # assert that the main queue has still been created
    stack.has_resource("SQSQueue"), "Queue was expected to be created"
    # and assert that the DLQ was not created
    stack.no_resource("MyDeadLetterQueue"), "DLQ was not expected to be created"

    # When the second queue is not being created, SQSQueue should not have an
    # empty value for the redrive policy set
    main_queue = stack.get_resource("SQSQueue")
    assert main_queue.get_property_value("RedrivePolicy") == ""
