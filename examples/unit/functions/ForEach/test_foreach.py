import json
from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template


def load_template(filename: str) -> Template:
    template_path = Path(__file__).parent / "templates" / filename

    return Template.from_yaml(template_path.resolve(), {})


def test_sns_replicate_transformed():

    template = load_template("replicate_sns.yaml")
    transformed_template = template.transform()

    # Render the transformed template
    rendered = transformed_template.render()

    expected_template = load_template("replicate_sns_transformed.yaml")

    # Compare just the Resources section
    assert rendered["Resources"] == expected_template.template["Resources"]

    # Transform section should still be present in the transformed template
    assert "Transform" in transformed_template.template
    assert transformed_template.template["Transform"] == "AWS::LanguageExtensions"


def test_sns_replicate():

    template = load_template("replicate_sns.yaml")

    stack = template.create_stack()

    sns_topics = stack.get_resources_of_type("AWS::SNS::Topic")
    assert len(sns_topics) == 4

    resource = stack.get_resource("SnsTopicSuccess")
    resource.assert_property_has_value("TopicName", "Success.fifo")

    resource = stack.get_resource("SnsTopicFailure")
    resource.assert_property_has_value("TopicName", "Failure.fifo")

    resource = stack.get_resource("SnsTopicTimeout")
    resource.assert_property_has_value("TopicName", "Timeout.fifo")

    resource = stack.get_resource("SnsTopicUnknown")
    resource.assert_property_has_value("TopicName", "Unknown.fifo")
