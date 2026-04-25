from itertools import product
from pathlib import Path

import pytest

from cloud_radar.cf.unit import Template


def load_template(filename: str) -> Template:
    template_path = Path(__file__).parent / "../../templates/ForEach" / filename

    return Template.from_yaml(template_path.resolve(), {})


def get_template_pairs():
    """Get all template pairs (original, transformed) from the templates directory."""
    templates_root_dir = Path(__file__).parent / "../../templates/ForEach"
    pairs = []

    # This one specifically requires parameters supplied to it, so we'll
    # check that separately
    excluded_templates = {"conditions/replicate_single_condition.yaml"}

    for subdir in ["resources", "outputs", "conditions"]:
        templates_dir = templates_root_dir / subdir
        for template_file in templates_dir.glob("*.yaml"):
            if not template_file.name.endswith("_transformed.yaml"):
                template_name = f"{subdir}/{template_file.name}"
                if template_name in excluded_templates:
                    continue
                transformed_file = template_file.with_name(
                    template_file.stem + "_transformed.yaml"
                )
                if transformed_file.exists():
                    pairs.append((template_name, f"{subdir}/{transformed_file.name}"))

    print(pairs)

    return pairs


@pytest.mark.parametrize("original_template,expected_template", get_template_pairs())
def test_foreach_transformed(original_template, expected_template):
    template = load_template(original_template)
    transformed_template = template.transform()

    # Render the transformed template
    rendered_stack = transformed_template.create_stack()

    expected = load_template(expected_template)
    expected_stack = expected.create_stack()

    # Compare the fully rendered Resources sections
    assert rendered_stack["Resources"] == expected_stack["Resources"]

    # Transform section should still be present in the transformed template
    assert "Transform" in transformed_template.template
    assert transformed_template.template["Transform"] == "AWS::LanguageExtensions"


def test_sns_replicate():

    template = load_template("resources/replicate_sns.yaml")

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


PARAMETER_VALUE_COMBINATIONS = [
    {
        "ParamA": value_a,
        "ParamB": value_b,
        "ParamC": value_c,
        "ParamD": value_d,
    }
    for value_a, value_b, value_c, value_d in product(["true", "false"], repeat=4)
]


@pytest.mark.parametrize("params", PARAMETER_VALUE_COMBINATIONS)
def test_replicate_single_condition_with_parameter_combinations(params):
    template = load_template("conditions/replicate_single_condition.yaml")
    transformed_template = template.transform(params=params)

    rendered = transformed_template.render(params=params)

    expected = load_template("conditions/replicate_single_condition_transformed.yaml")
    expected_rendered = expected.render(params=params)

    assert rendered["Conditions"] == expected_rendered["Conditions"]
    assert rendered["Resources"] == expected_rendered["Resources"]
