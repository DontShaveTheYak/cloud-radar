from pathlib import Path

import pytest

from cloud_radar.cf.unit._template import Template

"""Tests that the GetAtt function can use attribute values defined in a template."""


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/test_media_getatt.yaml"

    return Template.from_yaml(template_path.resolve(), {})


def test_outputs(template: Template):
    stack = template.create_stack()

    # These two outputs are expected to use values which came from the metadata override
    stack.get_output("ChannelIngestEndpointUrl1").assert_value_is(
        "http://one.example.com"
    )
    stack.get_output("ChannelIngestEndpointUrl2").assert_value_is(
        "http://two.example.com"
    )

    # This attribute will use the default format
    stack.get_output("ChannelArn").assert_value_is("MediaPackageV2Channel.Arn")
