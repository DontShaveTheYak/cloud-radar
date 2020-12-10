import inspect
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from cloud_radar.unit_test.template import (
    Template,
    add_metadata,
    r_equals,
    r_if,
    r_ref,
    r_sub,
)


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "./templates/log_bucket/log_bucket.yaml"

    return Template(template_path.resolve())


def test_default():
    template_path = Path(__file__).parent / "../templates/log_bucket/log_bucket.yaml"

    template = Template(template_path.resolve())

    assert isinstance(template.raw, str), "Should load a string instance of template"
    assert isinstance(
        template.template, dict
    ), "Should return a dictionary of the template"


def test_missing_template():

    with pytest.raises(FileNotFoundError):
        Template("fake.yml")


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch("cloud_radar.unit_test.template.load_yaml")
@patch("cloud_radar.unit_test.template.dump_yaml")
@patch("cloud_radar.unit_test.template.yaml")
def test_load(mock_yaml, mock_dump_yaml, mock_load_yaml, mock_open):
    template_dict = {"test": "test"}

    mock_load_yaml.return_value = template_dict

    mock_dump_yaml.return_value = str(template_dict)

    mock_yaml.load.return_value = template_dict

    template = Template("fake.yml")

    assert template.raw == str(
        template_dict
    ), "Should load a string version of our template"
    assert (
        template.template == template_dict
    ), "Should convert string dict to dict object"

    mock_load_yaml.assert_called_once_with(str(template_dict))
    mock_dump_yaml.assert_called_once_with(template_dict)
    mock_yaml.load.assert_called_once_with(str(template_dict))


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
@patch.object(Template, "set_parameters")
@patch.object(Template, "resolve_values")
def test_render_defaults(mock_resolve, mock_params, mock_load, mock_open):
    params = {"testParam": "Test Value"}
    region = "us-east-1"
    template_dict = {"test": "test"}

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    result = template.render(params)

    assert template.Region == region, "Should set a default region"

    mock_load.assert_called()
    mock_params.assert_called_once_with(params)
    mock_resolve.assert_called_once_with(template_dict)

    assert result == template_dict, "Should return resolved template."


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
@patch.object(Template, "set_parameters")
@patch.object(Template, "resolve_values")
def test_render_override(mock_resolve, mock_params, mock_load, mock_open):
    params = {"testParam": "Test Value"}
    region = "us-west-1"
    template_dict = {
        "Conditions": {"test": False},
        "Resources": {"test": {"Condition": "test"}, "test2": {}},
    }

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    result = template.render(params, region)

    assert template.Region == region, "Should use our passed in region"

    assert result["Resources"] == {"test2": {}}, "Should remove test resource"


def test_ref():

    template = {"Parameters": {"foo": {"Value": "bar"}}}

    add_metadata(template, Template.Region)

    for i in inspect.getmembers(Template):
        if not i[0].startswith("_"):
            if not inspect.ismethod(i[1]):
                result = r_ref(template, f"AWS::{i[0]}")
                assert (
                    result == i[1]
                ), "Should be able to reference all pseudo variables."

    result = r_ref(template, "foo")

    assert result == "bar", "Should reference parameters."

    result = r_ref(template, "SomeResource")

    assert (
        result == "SomeResource"
    ), "If not a psedo var or parameter it should return the input."


def test_if():

    template = {"Conditions": {"test": False}}

    result = r_if(template, ["test", "true_value", "false_value"])

    assert result == "false_value", "Should return the false value."

    template["Conditions"]["test"] = True

    result = r_if(template, ["test", "true_value", "false_value"])

    assert result == "true_value", "Should return the true value."

    with pytest.raises((Exception)):
        # First value should the name of the condition to lookup
        r_if(template, [True, "True", "False"])


def test_equals():
    # AWS is not very clear on what is valid here?
    # > A value of any type that you want to compare.

    true_lst = [True, "foo", 5, ["test"], {"foo": "foo"}]
    false_lst = [False, "bar", 10, ["bar"], {"bar": "bar"}]

    for idx, true in enumerate(true_lst):
        false = false_lst[idx]

        assert r_equals([true, true]), f"Should compare {type(true)} as True."

        assert not r_equals([true, false]), f"Should compare {type(true)} as False."


def test_sub():
    template_dict = {"Parameters": {"Foo": {"Value": "bar"}}}

    assert (
        r_sub(template_dict, "Foo ${Foo}") == "Foo bar"
    ), "Should subsuite a parameter."

    result = r_sub(template_dict, "not ${!Test}")

    assert result == "not ${Test}", "Should return a string literal."

    add_metadata(template_dict, "us-east-1")

    result = r_sub(template_dict, "${AWS::Region} ${Foo} ${!BASH_VAR}")

    assert result == "us-east-1 bar ${BASH_VAR}", "Should render multiple variables."


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
def test_resolve(mock_load, mock_open):
    template_dict = {
        "Parameters": {"Test": {"Value": "test"}},
        "Conditions": {"test": True},
    }

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    result = template.resolve_values({"Ref": "Test"})

    assert result == "test", "Should resolve the value from the template."

    result = template.resolve_values({"Ref": "Test2"})

    assert result == "Test2", "Should return its self if not a parameter."

    result = template.resolve_values({"level1": {"Fn::If": ["test", "True", "False"]}})

    assert result == {"level1": "True"}, "Should resolve nested dicts."

    result = template.resolve_values(
        [{"level1": {"Fn::If": ["test", "True", "False"]}}]
    )

    assert result == [{"level1": "True"}], "Should resolve nested lists."

    result = template.resolve_values("test")

    assert result == "test", "Should return regular strings."


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
def test_set_params(mock_load, mock_open):
    template_dict = {}

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    template.set_parameters()

    assert template.template == {}, "Should do nothing if no parameters in template."

    template.template = {"Parameters": {"Test": {}}}

    with pytest.raises(Exception):
        template.set_parameters()

    template.set_parameters({"Test": "value"})

    assert {"Test": {"Value": "value"}} == template.template[
        "Parameters"
    ], "Should set the value to what we pass in."

    template.template = {"Parameters": {"Test": {"Default": "default"}}}

    template.set_parameters()

    assert {"Test": {"Default": "default", "Value": "default"}} == template.template[
        "Parameters"
    ], "Should set default values."
