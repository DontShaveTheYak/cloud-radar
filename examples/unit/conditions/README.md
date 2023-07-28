
# What does this example cover?

This example shows two main scenarios:
* That Conditionals in your template evaluate to the correct value.
* Conditional resources were created or not.


It uses [this AWS Labs sample template](https://github.com/awslabs/aws-cloudformation-templates/blob/1de97eda75e3b876b8fcb0166d2d4c0691bdcdf5/aws/services/SQS/SQSStandardQueue.json), that includes a condition for if an SQS Queue should have a Dead Letter Queue configured for it or not. This uses a pretty simple condition that simply checks if a parameter value was set to `true`, but this can be as compicated as your template requires.

```json
    "Conditions": {
        "CreateDeadLetterQueue": {
            "Fn::Equals": [
                {
                    "Ref": "UsedeadletterQueue"
                },
                "true"
            ]
        }
    }
```


The rendered stack includes a number of method for determining if your conditions worked as epected.

These methods can be used to assert if named resources exist or not:
```python
    # assert that the main queue has still been created
    stack.has_resource("SQSQueue"), "Queue was expected to be created"

    # and assert that the DLQ was not created
    stack.no_resource("MyDeadLetterQueue"), "DLQ was not expected to be created"
```

You also can also perform assertions based on the number of resources of a type that were created:
```python
    sqs_resources = stack.get_resources_of_type("AWS::SQS::Queue")
    assert len(sqs_resources) == 2
```

This example also includes a resource property that is conditionally set with this template definition:
```json
    "RedrivePolicy": {
        "Fn::If": [
            "CreateDeadLetterQueue",
            {
                "deadLetterTargetArn": {
                    "Fn::GetAtt": [
                        "MyDeadLetterQueue",
                        "Arn"
                    ]
                },
                "maxReceiveCount": 5
            },
            {
                "Ref": "AWS::NoValue"
            }
        ]
    }
```

A test case is able to check that when the DLQ was not created, that this redrive policy was not set:
```python
    # When the second queue is not being created, SQSQueue should not have an
    # empty value for the redrive policy set
    main_queue = stack.get_resource("SQSQueue")
    assert main_queue.get_property_value("RedrivePolicy") == ''
```

Or inversly that it was set and referenced the correct target queue:
```python
    # When the second queue is being created, the SQSQueue should have a
    # redrive policy set referring to it
    main_queue = stack.get_resource("SQSQueue")
    redrive_policy = main_queue.get_property_value("RedrivePolicy")
    assert redrive_policy.get("deadLetterTargetArn") == "MyDeadLetterQueue.Arn"
```
