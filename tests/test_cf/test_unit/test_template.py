from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from cloud_radar.cf.unit import functions
from cloud_radar.cf.unit._template import (
    Template,
    add_metadata,
)


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve(), {})


def test_constructor(template: Template):
    with pytest.raises(TypeError) as e:
        Template("not a dict")  # type: ignore

    assert "Template should be a dict, not str." in str(e)

    with pytest.raises(TypeError) as e:
        Template({}, "")  # type: ignore

    assert "Imports should be a dict, not str." in str(e)

    assert isinstance(template.raw, str), "Should load a string instance of template"
    assert isinstance(
        template.template, dict
    ), "Should return a dictionary of the template"
    assert (
        template.Region == Template.Region
    ), "Should set the default region from the class."


@patch("builtins.open", new_callable=mock_open, read_data="{'Foo': 'bar'}")
def test_from_yaml(mock_open):
    template_dict = {"Foo": "bar"}

    template = Template.from_yaml("fake.yml")

    assert template.raw == "Foo: bar\n", "Should load a string version of our template"
    assert (
        template.template == template_dict
    ), "Should convert string dict to dict object"


def test_render_true():
    t = {
        "Parameters": {"testParam": {"Default": "Test Value"}},
        "Conditions": {"Bar": {"Fn::Equals": [{"Ref": "testParam"}, "Test Value"]}},
        "Resources": {"Foo": {"Condition": "Bar", "Properties": {}}},
    }

    template = Template(t)

    result = template.render()

    assert t is not result, "Should not pass back a pointer to the same dict."

    assert template.Region == Template.Region, "Should set the default region."

    assert "Foo" in result["Resources"], "Resources should not be empty."

    assert result["Conditions"]["Bar"], "Condition should be true."

    assert result["Metadata"], "Metadata should be set."


def test_render_false():
    params = {"testParam": "Not Test Value"}

    t = {
        "Parameters": {"testParam": {"Default": "Test Value"}},
        "Conditions": {"Bar": {"Fn::Equals": [{"Ref": "testParam"}, "Test Value"]}},
        "Resources": {
            "Foo": {"Condition": "Bar", "Properties": {}},
            "Foobar": {
                "Properties": {"Something": {"Fn::Sub": "This is a ${testParam}"}}
            },
        },
    }

    template = Template(t)

    result = template.render(params, region="us-west-2")

    assert template.Region != Template.Region, "Should not set the default region."

    assert "Foo" not in result["Resources"], "Resources should be empty."

    assert not result["Conditions"]["Bar"], "Condition should be false."


def test_render_invalid_ref():
    t = {
        "Parameters": {"testParam": {"Default": "Test Value"}},
        "Conditions": {"Bar": {"Fn::Equals": [{"Ref": "testParam"}, "Test Value"]}},
        "Resources": {
            "Foo": {"Condition": "Bar", "Properties": {"Name": {"Ref": "FAKE!"}}}
        },
    }

    template = Template(t)

    with pytest.raises(Exception) as ex:
        _ = template.render()

    assert "not a valid Resource" in str(ex)


def test_resolve():
    t = {
        "Parameters": {"Test": {"Value": "test"}},
        "Conditions": {"test": True},
        "Resources": {},
    }

    template = Template(t)

    result = template.resolve_values({"Ref": "Test"}, functions.ALL_FUNCTIONS)

    assert result == "test", "Should resolve the value from the template."

    with pytest.raises(Exception) as ex:
        result = template.resolve_values({"Ref": "Test2"}, functions.ALL_FUNCTIONS)

    assert "not a valid Resource" in str(ex)

    result = template.resolve_values(
        {"level1": {"Fn::If": ["test", "True", "False"]}}, functions.ALL_FUNCTIONS
    )

    assert result == {"level1": "True"}, "Should resolve nested dicts."

    result = template.resolve_values(
        [{"level1": {"Fn::If": ["test", "True", "False"]}}], functions.ALL_FUNCTIONS
    )

    assert result == [{"level1": "True"}], "Should resolve nested lists."

    result = template.resolve_values("test", functions.ALL_FUNCTIONS)

    assert result == "test", "Should return regular strings."


def test_function_order():
    t = {
        "Parameters": {"Test": {"Value": "test"}},
        "Conditions": {"test": True},
    }

    template = Template(t)

    test_if = {
        "Fn::Cidr": {
            "Fn::If": "select",
        }
    }

    with pytest.raises(ValueError) as ex:
        _ = template.resolve_values(test_if, functions.ALL_FUNCTIONS)

    assert "Fn::If with value" in str(ex)

    with pytest.raises(ValueError) as ex:
        _ = template.resolve_values({"Fn::Base64": ""}, functions.CONDITIONS)

    assert "Fn::Base64 with value" in str(ex)

    with pytest.raises(ValueError) as ex:
        _ = template.resolve_values({"Fn::Not": ""}, functions.INTRINSICS)

    assert "Fn::Not with value" in str(ex)


def test_set_params():
    t = {}
    params = {"Foo": {"Bar"}}

    template = Template(t)

    template.set_parameters()

    assert template.template == {}, "Should do nothing if no parameters in template."

    with pytest.raises(ValueError) as e:
        template.set_parameters(params)

    assert "You supplied parameters for a template that doesn't have any." in str(
        e.value
    ), "Should throw correct exception."

    template.template = {"Parameters": {"Test": {}}}

    with pytest.raises(ValueError) as e:
        template.set_parameters()

    assert "Must provide values for parameters that don't have a default value." in str(
        e.value
    ), "Should throw correct exception."

    template.set_parameters({"Test": "value"})

    assert {"Test": {"Value": "value"}} == template.template[
        "Parameters"
    ], "Should set the value to what we pass in."

    with pytest.raises(ValueError) as e:
        template.set_parameters({"Bar": "Foo"})

    assert "You passed a Parameter that was not in the Template." in str(
        e.value
    ), "Should throw correct exception."

    template.template = {"Parameters": {"Test": {"Default": "default"}}}

    template.set_parameters()

    assert {"Test": {"Default": "default", "Value": "default"}} == template.template[
        "Parameters"
    ], "Should set default values."


@pytest.mark.parametrize("t", [{}, {"Metadata": {}}])
def test_metadata(t):
    region = "us-east-1"
    add_metadata(t, region=region)

    assert "Metadata" in t

    assert region == t["Metadata"]["Cloud-Radar"]["Region"]


def test_render_condition_keys():
    t = {
        "Parameters": {"testParam": {"Default": "Test Value"}},
        "Conditions": {
            "Bar": {
                "Fn::Equals": [
                    {"Ref": "testParam"},
                    "Test Value",
                ]
            },
            "Foo": {
                "Fn::Or": [
                    {"Condition": "Bar"},
                    False,
                ]
            },
        },
        "Resources": {
            "Foo": {
                "Condition": "Bar",
                "Properties": {
                    "NotFunction": {
                        "Condition": {
                            "IAM": "PolicyCondition!",
                        },
                    },
                    "IsFunction": {
                        "Condition": "Bar",
                    },
                },
            },
        },
    }

    template = Template(t)

    result = template.render()

    resource_props = result["Resources"]["Foo"]["Properties"]

    assert isinstance(resource_props["NotFunction"]["Condition"], dict)

    assert resource_props["IsFunction"] is True

    assert result["Conditions"]["Foo"] is True

    result = template.render({"testParam": "some value"})

    assert result["Conditions"]["Foo"] is False
