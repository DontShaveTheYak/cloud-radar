from pathlib import Path

import pytest
import yaml

from cloud_radar.cf.unit._template import Template

"""Tests some edge cases for the Sub function"""


@pytest.fixture
def template():
    template_path = (
        Path(__file__).parent / "../../templates/test_sub_default_number.yaml"
    )

    return Template.from_yaml(
        template_path.resolve(),
        dynamic_references={
            "ssm": {
                "/dummy/dev/us-east-1/aurora/cluster/1/sec-grp/id": "sg-1234567",
                "/dummy/dev/us-east-1/aurora/cluster/2/sec-grp/id": "sg-7654321",
                "/dummy/dev/us-east-1/vpc/id/horizontal-vpc": "vpc-123456",
            }
        },
    )


def test_with_default_number(template: Template):
    stack = template.create_stack()

    # Check our value resolved. Not really required, as it will have
    # errorred before it gets this far if it couldn't find the lookup value
    security_group_resource = stack.get_resource("rFunctionSecurityGroup")
    security_group_egress = security_group_resource.get_property_value(
        "SecurityGroupEgress"
    )

    assert len(security_group_egress) == 1
    assert security_group_egress[0]["DestinationSecurityGroupId"] == "sg-1234567"


def test_with_supplied_value(template: Template):
    stack = template.create_stack(params={"pTargetDatabaseClusterNumber": "2"})

    # Check our value resolved. Not really required, as it will have
    # errorred before it gets this far if it couldn't find the lookup value
    security_group_resource = stack.get_resource("rFunctionSecurityGroup")
    security_group_egress = security_group_resource.get_property_value(
        "SecurityGroupEgress"
    )

    assert len(security_group_egress) == 1
    assert security_group_egress[0]["DestinationSecurityGroupId"] == "sg-7654321"
