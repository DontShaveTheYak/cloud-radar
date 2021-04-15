import inspect

import pytest

from cloud_radar.cf.unit import functions
from cloud_radar.cf.unit._template import Template, add_metadata


@pytest.fixture(scope="session")
def fake_t() -> Template:
    return Template({})


def test_base64(fake_t: Template):
    value = 1

    with pytest.raises(Exception) as e:
        result = functions.base64(fake_t, value)

    assert "The value for !Base64 or Fn::Base64 must be a String, not int." in str(
        e.value
    )

    value = "TestString"

    result = functions.base64(fake_t, value)

    assert result == "VGVzdFN0cmluZw=="


def test_cidr(fake_t: Template):

    with pytest.raises(Exception) as e:
        result = functions.cidr(fake_t, {})

    assert "must be a List, not" in str(e)

    with pytest.raises(Exception) as e:
        result = functions.cidr(fake_t, [1])

    assert "a ipBlock, the count of subnets and the cidrBits." in str(e)

    value = ["192.168.0.0/24", 6, 5]

    expected = [
        "192.168.0.0/27",
        "192.168.0.32/27",
        "192.168.0.64/27",
        "192.168.0.96/27",
        "192.168.0.128/27",
        "192.168.0.160/27",
    ]

    result = functions.cidr(fake_t, value)

    assert result == expected

    value[1] = 9
    with pytest.raises(Exception) as e:
        result = functions.cidr(fake_t, value)

    assert "unable to convert" in str(e)


def test_ref():

    template = {"Parameters": {"foo": {"Value": "bar"}}}

    add_metadata(template, Template.Region)

    template = Template(template)

    for i in inspect.getmembers(Template):
        if not i[0].startswith("_"):
            if isinstance(i[1], str):
                result = functions.ref(template, f"AWS::{i[0]}")
                assert (
                    result == i[1]
                ), "Should be able to reference all pseudo variables."

    result = functions.ref(template, "foo")

    assert result == "bar", "Should reference parameters."

    result = functions.ref(template, "SomeResource")

    assert (
        result == "SomeResource"
    ), "If not a psedo var or parameter it should return the input."

    fake = "AWS::FakeVar"

    with pytest.raises(ValueError) as e:
        functions.ref(template, fake)

    assert f"Unrecognized AWS Pseduo variable: '{fake}'." in str(e.value)


def test_if(fake_t: Template):

    template = {"Conditions": {"test": False}}

    fake_t.template = template

    result = functions.if_(fake_t, ["test", "true_value", "false_value"])

    assert result == "false_value", "Should return the false value."

    template["Conditions"]["test"] = True

    result = functions.if_(fake_t, ["test", "true_value", "false_value"])

    assert result == "true_value", "Should return the true value."

    with pytest.raises(Exception):
        # First value should the name of the condition to lookup
        functions.if_(fake_t, [True, "True", "False"])


def test_join(fake_t: Template):

    value = [":", ["a", "b", "c"]]

    result = functions.join(fake_t, value)

    assert result == "a:b:c"

    value = {}

    with pytest.raises(Exception) as e:
        result = functions.join(fake_t, value)

    assert "must be list not dict" in str(e.value)

    value = ["a", "b", "c"]

    with pytest.raises(Exception) as e:
        result = functions.join(fake_t, value)

    assert "must contain a delimiter and a list of items to join." in str(e.value)

    value = [1, {}]

    with pytest.raises(Exception) as e:
        result = functions.join(fake_t, value)

    assert (
        "The first value for !Join or Fn::Join must be a String and the second a List."
        in str(e.value)
    )


def test_equals(fake_t: Template):
    # AWS is not very clear on what is valid here?
    # > A value of any type that you want to compare.

    true_lst = [True, "foo", 5, ["test"], {"foo": "foo"}]
    false_lst = [False, "bar", 10, ["bar"], {"bar": "bar"}]

    for idx, true in enumerate(true_lst):
        false = false_lst[idx]

        assert functions.equals(
            fake_t, [true, true]
        ), f"Should compare {type(true)} as True."

        assert not functions.equals(
            fake_t, [true, false]
        ), f"Should compare {type(true)} as False."


def test_sub():
    template_dict = {"Parameters": {"Foo": {"Value": "bar"}}}

    template = Template(template_dict)

    assert (
        functions.sub(template, "Foo ${Foo}") == "Foo bar"
    ), "Should subsuite a parameter."

    result = functions.sub(template, "not ${!Test}")

    assert result == "not ${Test}", "Should return a string literal."

    add_metadata(template_dict, "us-east-1")

    template = Template(template_dict)

    result = functions.sub(template, "${AWS::Region} ${Foo} ${!BASH_VAR}")

    assert result == "us-east-1 bar ${BASH_VAR}", "Should render multiple variables."
