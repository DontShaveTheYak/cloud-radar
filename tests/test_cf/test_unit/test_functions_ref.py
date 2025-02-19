from pathlib import Path

import pytest
import yaml

from cloud_radar.cf.unit._template import Template

"""Tests that the Ref function can use metadata defined in a template."""


@pytest.fixture
def template():
    template_path = (
        Path(__file__).parent / "../../templates/test_imagebuilder_image_ref.yaml"
    )

    return Template.from_yaml(template_path.resolve(), {})


def test_outputs(template: Template):
    # As well as setting the resource metadata in the template file itself, we can
    # programmatically do the same thing
    image_arn = "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-image"
    metadata = {"Cloud-Radar": {"ref": image_arn}}
    template.template["Resources"]["DummyEcrImage"]["Metadata"] = metadata

    # When rendering the stack, it reloads the "raw" so need to reset that back with the modified content
    template.raw = yaml.dump(template.template)

    stack = template.create_stack()

    # These outputs are expected to use the metadata override
    stack.get_output("ImageArn").assert_value_is(image_arn)
    stack.get_output("ImageName").assert_value_is("my-example-image")

    # This attribute will use the default format
    stack.get_output("ChannelArn").assert_value_is("MediaPackageV2Channel")
