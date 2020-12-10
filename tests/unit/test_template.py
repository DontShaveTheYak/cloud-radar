from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from cloud_radar.unit_test import Template


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


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
def test_if(mock_load, mock_open):
    template_dict = {"Conditions": {"test": True}}

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    result = template.r_if([False, "True", "False"])

    assert result == "False", "Should return string false."

    result = template.r_if(["test", "True", "False"])

    assert result == "True", "Should return string true."


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
def test_equals(mock_load, mock_open):
    template_dict = {"test": "test"}

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    result = template.r_equals([True, False])

    assert not result, "Should be false"

    result = template.r_equals(["True", "True"])

    assert result, "Should return true"


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
def test_sub(mock_load, mock_open):
    template_dict = {"Parameters": {"Test": {"Value": "test"}}}

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    template.Region = "us-east-1"

    result = template.r_sub("${Test}")

    assert result == "test", "Should return the value from the template."

    result = template.r_sub("not ${!Test}")

    assert result == "not ${Test}", "Should return a string literal."

    result = template.r_sub("${AWS::Region}")

    assert result == template.Region, "Should render Pseudo parameters."

    result = template.r_sub("${AWS::Region} ${Test} ${!BASH_VAR}")

    assert result == "us-east-1 test ${BASH_VAR}", "Should render multiple parameters."

    result = template.r_sub("${AWS::AccountId}")

    assert result == Template.AccountId, "Should render pseduovars."


@patch("builtins.open", new_callable=mock_open, read_data="{'test': 'test'}")
@patch.object(Template, "load")
def test_resolve(mock_load, mock_open):
    template_dict = {"Parameters": {"Test": {"Value": "test"}}}

    mock_load.return_value = template_dict

    template = Template("fake.yml")

    result = template.resolve_values({"Ref": "Test"})

    assert result == "test", "Should resolve the value from the template."

    result = template.resolve_values({"Ref": "Test2"})

    assert result == "Test2", "Should return its self if not a parameter."

    result = template.resolve_values({"level1": {"Fn::If": [True, "True", "False"]}})

    assert result == {"level1": "True"}, "Should resolve nested dicts."

    result = template.resolve_values([{"level1": {"Fn::If": [True, "True", "False"]}}])

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
