import inspect
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from cloud_radar.cf.unit._template import (
    Template,
    add_metadata,
    r_equals,
    r_if,
    r_ref,
    r_sub,
)


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../../templates/log_bucket/log_bucket.yaml"

    return Template.from_yaml(template_path.resolve())


def test_default(template: Template):

    assert isinstance(template.raw, str), "Should load a string instance of template"
    assert isinstance(
        template.template, dict
    ), "Should return a dictionary of the template"
    assert (
        template.Region == Template.Region
    ), "Should set the default region from the class."


def test_missing_template():

    with pytest.raises(TypeError):
        Template("not a dict")


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
        "Resources": {"Foo": {"Condition": "Bar"}},
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
            "Foo": {"Condition": "Bar"},
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

    fake = "AWS::FakeVar"

    with pytest.raises(ValueError) as e:
        r_ref(template, fake)

    assert f"Unrecognized AWS Pseduo variable: '{fake}'." in str(e.value)


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


def test_resolve():
    t = {
        "Parameters": {"Test": {"Value": "test"}},
        "Conditions": {"test": True},
    }

    template = Template(t)

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


def test_log_defaults(template):

    result = template.render({"BucketPrefix": "testing"})

    assert "LogsBucket" in result["Resources"]

    bucket_name = result["Resources"]["LogsBucket"]["Properties"]["BucketName"]

    assert "us-east-1" in bucket_name


def test_log_retain(template):

    result = template.render(
        {"BucketPrefix": "testing", "KeepBucket": "TRUE"}, region="us-west-2"
    )

    assert "LogsBucket" not in result["Resources"]

    bucket = result["Resources"]["RetainLogsBucket"]

    assert "DeletionPolicy" in bucket

    assert bucket["DeletionPolicy"] == "Retain"

    bucket_name = bucket["Properties"]["BucketName"]

    assert "us-west-2" in bucket_name
