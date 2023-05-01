from __future__ import with_statement

import inspect
from typing import Any, Dict

import pytest

from cloud_radar.cf.unit import functions
from cloud_radar.cf.unit._template import Template, add_metadata


@pytest.fixture(scope="session")
def fake_t() -> Template:
    return Template({})


def test_base64(fake_t: Template):
    value = 1

    with pytest.raises(TypeError) as e:
        result = functions.base64(fake_t, value)

    assert "must be a String, not int." in str(e.value)

    value = "TestString"

    result = functions.base64(fake_t, value)

    assert result == "VGVzdFN0cmluZw=="


def test_cidr(fake_t: Template):
    with pytest.raises(TypeError) as e:
        result = functions.cidr(fake_t, {})

    assert "must be a List, not" in str(e)

    with pytest.raises(ValueError) as e:
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


def test_and(fake_t):
    with pytest.raises(TypeError) as e:
        result = functions.and_(fake_t, {})

    assert "List, not dict." in str(e)

    with pytest.raises(ValueError) as e:
        result = functions.and_(fake_t, [True])

    assert "between 2 and 10 conditions." in str(e)

    with pytest.raises(ValueError) as e:
        result = functions.and_(fake_t, [True] * 11)

    assert "between 2 and 10 conditions." in str(e)

    result = functions.and_(fake_t, [True, True])

    assert result is True

    result = functions.and_(fake_t, [True, False])

    assert result is False

    result = functions.and_(fake_t, [False, False])

    assert result is False


def test_equals(fake_t: Template):
    # AWS is not very clear on what is valid here?
    # > A value of any type that you want to compare.

    with pytest.raises(TypeError):
        functions.equals(fake_t, {})

    with pytest.raises(ValueError):
        functions.equals(fake_t, [0])

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


def test_if(fake_t: Template):
    template = {"Conditions": {"test": False}}

    fake_t.template = template

    with pytest.raises(TypeError) as e:
        result = functions.if_(fake_t, {})

    assert "must be a List, not dict." in str(e.value)

    with pytest.raises(ValueError) as e:
        result = functions.if_(fake_t, [0])

    assert "True value and a False value." in str(e.value)

    with pytest.raises(TypeError) as e:
        result = functions.if_(fake_t, [0, 0, 0])

    assert "Condition should be a String, not int." in str(e.value)

    result = functions.if_(fake_t, ["test", "true_value", "false_value"])

    assert result == "false_value", "Should return the false value."

    template["Conditions"]["test"] = True

    result = functions.if_(fake_t, ["test", "true_value", "false_value"])

    assert result == "true_value", "Should return the true value."

    with pytest.raises(TypeError):
        # First value should the name of the condition to lookup
        functions.if_(fake_t, [True, "True", "False"])


def test_not(fake_t):
    with pytest.raises(TypeError) as e:
        result = functions.not_(fake_t, {})

    assert "must be a List, not dict." in str(e.value)

    with pytest.raises(ValueError) as e:
        result = functions.not_(fake_t, [True, True])

    assert "must contain a single Condition." in str(e.value)

    result = functions.not_(fake_t, [True])

    assert result is False

    result = functions.not_(fake_t, [False])

    assert result is True


def test_or(fake_t):
    with pytest.raises(TypeError) as e:
        result = functions.or_(fake_t, {})

    assert "must be a List, not dict." in str(e.value)

    with pytest.raises(ValueError) as e:
        result = functions.or_(fake_t, [True])

    assert "between 2 and 10 conditions." in str(e.value)

    with pytest.raises(ValueError) as e:
        result = functions.or_(fake_t, [True] * 11)

    assert "between 2 and 10 conditions." in str(e.value)

    result = functions.or_(fake_t, [True, True])

    assert result is True

    result = functions.or_(fake_t, [True, False])

    assert result is True

    result = functions.or_(fake_t, [False, False])

    assert result is False


def test_condition():
    template = {"Conditions": {"test": False}}

    template = Template(template)

    with pytest.raises(TypeError) as e:
        result = functions.condition(template, [])

    assert "String, not list." in str(e)

    with pytest.raises(KeyError) as e:
        result = functions.condition(template, "Fake")

    assert "Unable to find condition" in str(e)

    result = functions.condition(template, "test")

    assert result is False


def test_find_in_map():
    template = {}

    add_metadata(template, Template.Region)

    template = Template(template)

    with pytest.raises(TypeError) as e:
        functions.find_in_map(template, {})

    assert "must be a List, not dict." in str(e)

    with pytest.raises(ValueError) as e:
        functions.find_in_map(template, [0])

    assert "a MapName, TopLevelKey and SecondLevelKey." in str(e)

    map_name = "TestMap"
    first_key = "FirstKey"
    second_key = "SecondKey"

    values = [map_name, first_key, second_key]

    with pytest.raises(KeyError) as e:
        functions.find_in_map(template, values)

    assert "Unable to find Mappings section in template." in str(e)

    template.template["Mappings"] = {}

    with pytest.raises(KeyError) as e:
        functions.find_in_map(template, values)

    assert f"Unable to find {map_name} in Mappings section of template." in str(e)

    template.template["Mappings"][map_name] = {}

    with pytest.raises(KeyError) as e:
        functions.find_in_map(template, values)

    assert f"Unable to find key {first_key}" in str(e)

    template.template["Mappings"][map_name][first_key] = {}

    with pytest.raises(KeyError) as e:
        functions.find_in_map(template, values)

    assert f"Unable to find key {second_key}" in str(e)

    expected = "ExpectedValue"

    template.template["Mappings"][map_name][first_key][second_key] = expected

    result = functions.find_in_map(template, values)

    assert result == expected


def test_get_att():
    template = {"Resources": {}}

    add_metadata(template, Template.Region)

    template = Template(template)

    with pytest.raises(TypeError) as e:
        functions.get_att(template, {})

    assert "Fn::GetAtt - The values must be a List, not dict." in str(e)

    with pytest.raises(ValueError) as e:
        functions.get_att(template, [0])

    assert "the logicalNameOfResource and attributeName." in str(e)

    with pytest.raises(TypeError) as e:
        functions.get_att(template, [0, 0])

    assert "logicalNameOfResource and attributeName must be String." in str(e)

    resource_name = "TestA"
    att = "TestAttribute"

    values = [resource_name, att]

    with pytest.raises(KeyError) as e:
        functions.get_att(template, values)

    assert f"{resource_name} not found in template." in str(e)

    template.template["Resources"]["TestA"] = {}

    result = functions.get_att(template, values)

    assert result == f"{resource_name}.{att}"


def test_get_az(fake_t: Template, mocker):
    mock_fetch = mocker.patch.object(functions, "get_region_azs")
    mock_fetch.return_value = ["us-east-1-az-1", "us-east-1-az-2"]

    with pytest.raises(TypeError) as e:
        result = functions.get_azs(fake_t, [])

    assert "region must be a String, not list." in str(e)

    region = "us-east-1"

    result = functions.get_azs(fake_t, region)

    for az in result:
        assert region in az


def test_get_az_no_region(fake_t: Template, mocker):
    mock_fetch = mocker.patch.object(functions, "get_region_azs")
    mock_fetch.return_value = ["us-east-1-az-1", "us-east-1-az-2"]

    functions.get_azs(fake_t, "")

    functions.get_azs(fake_t, None)


def test_get_region_azs(mocker):
    region_name = "us-east-1"

    mocker.patch.object(functions, "REGION_DATA", None)
    mock_fetch = mocker.patch.object(functions, "_fetch_region_data")
    mock_fetch.return_value = [{"code": "SomeRegion"}]

    with pytest.raises(Exception) as e:
        result = functions.get_region_azs(region_name)

    mock_fetch.assert_called()
    assert f"Unable to find region {region_name}." in str(e)

    region_data = [
        {"code": "us-east-1", "zones": ["us-east-1e", "us-east-1f"]},
        {"code": "us-east-2", "zones": ["us-east-2a", "us-east-2c"]},
    ]

    mocker.resetall()

    mocker.patch.object(functions, "REGION_DATA", region_data)

    result = functions.get_region_azs(region_name)

    mock_fetch.assert_not_called()

    for az in result:
        assert region_name in az


def test_fetch_region_data(mocker):
    mock_post = mocker.patch("cloud_radar.cf.unit.functions.requests.get")
    mock_json = mocker.patch("cloud_radar.cf.unit.functions.json.loads")
    mock_json.return_value = "TestData"

    mock_r = mock_post.return_value

    mock_r.status_code = 200

    result = functions._fetch_region_data()

    assert result == "TestData"

    mock_r.raise_for_status.assert_not_called()

    assert result == "TestData"

    mock_r.status_code = 500

    functions._fetch_region_data()

    mock_r.raise_for_status.assert_called()


def test_import_value():
    name = "TestImport"
    value = "TestValue"

    imports = {}

    template = Template({}, imports)

    with pytest.raises(TypeError) as e:
        result = functions.import_value(template, [])

    assert "Export should be String, not list." in str(e)

    with pytest.raises(ValueError) as e:
        result = functions.import_value(template, name)

    assert "No imports have been configued" in str(e)

    imports["FakeTest"] = "Fake"

    with pytest.raises(KeyError) as e:
        result = functions.import_value(template, name)

    assert f"{name} not found" in str(e)

    imports[name] = value

    result = functions.import_value(template, name)

    assert result == value


def test_join(fake_t: Template):
    value = [":", ["a", "b", "c"]]

    result = functions.join(fake_t, value)

    assert result == "a:b:c"

    value: Dict[str, Any] = {}

    with pytest.raises(TypeError) as e:
        result = functions.join(fake_t, value)

    assert "must be a List, not dict" in str(e.value)

    value = ["a", "b", "c"]

    with pytest.raises(ValueError) as e:
        result = functions.join(fake_t, value)

    assert "must contain a delimiter and a list of items to join." in str(e.value)

    value = [1, {}]

    with pytest.raises(TypeError) as e:
        result = functions.join(fake_t, value)

    assert "must be a String and the second a List." in str(e.value)


def test_select(fake_t):
    with pytest.raises(TypeError) as e:
        result = functions.select(fake_t, {})

    assert "must be a List, not dict." in str(e)

    with pytest.raises(ValueError) as e:
        result = functions.select(fake_t, [0])

    assert "an index and a list of items to select from." in str(e)

    with pytest.raises(TypeError) as e:
        result = functions.select(fake_t, [0, 0])

    assert "be a Number and the second a List." in str(e)

    with pytest.raises(IndexError) as e:
        result = functions.select(fake_t, [5, ["Test"] * 3])

    assert "smaller than the Index given." in str(e)

    result = functions.select(fake_t, [2, ["1", "2", "3"]])

    assert result == "3"


def test_split(fake_t):
    with pytest.raises(TypeError) as e:
        result = functions.split(fake_t, {})

    assert "must be a List, not dict." in str(e)

    with pytest.raises(ValueError) as e:
        result = functions.split(fake_t, [0])

    assert "a delimiter and a String to split." in str(e)

    with pytest.raises(TypeError) as e:
        result = functions.split(fake_t, [0, 0])

    assert "String and the second a String." in str(e)

    result = functions.split(fake_t, [",", "A,B,C"])

    assert result == ["A", "B", "C"]


def test_sub(mocker):
    template_dict = {"Parameters": {"Foo": {"Value": "bar"}}}

    template = Template(template_dict)

    mock_s = mocker.patch.object(functions, "sub_s", autospec=True)
    mock_l = mocker.patch.object(functions, "sub_l", autospec=True)

    with pytest.raises(TypeError) as e:
        functions.sub(template, {})

    assert "String or List, not dict." in str(e)

    functions.sub(template, "")

    mock_s.assert_called()
    mock_l.assert_not_called()

    mocker.resetall()

    functions.sub(template, [])

    mock_l.assert_called()
    mock_s.assert_not_called()


def test_sub_s():
    template_dict = {"Parameters": {"Foo": {"Value": "bar"}}}

    template = Template(template_dict)

    result = functions.sub_s(template, "Foo ${Foo}")

    assert result == "Foo bar", "Should subsuite a parameter."

    result = functions.sub_s(template, "not ${!Test}")

    assert result == "not ${Test}", "Should return a string literal."

    add_metadata(template_dict, "us-east-1")

    template = Template(template_dict)

    result = functions.sub(template, "${AWS::Region} ${Foo} ${!BASH_VAR}")

    assert result == "us-east-1 bar ${BASH_VAR}", "Should render multiple variables."


def test_sub_l():
    template_dict = {"Parameters": {"Foo": {"Value": "bar"}}}

    add_metadata(template_dict, "us-east-1")

    template = Template(template_dict)

    with pytest.raises(ValueError) as e:
        functions.sub_l(template, [0])

    assert "source string and a Map of variables." in str(e)

    with pytest.raises(TypeError) as e:
        functions.sub_l(template, [0, 0])

    assert "String and the second a Map." in str(e)

    var_map = {"LocalA": "TestA"}

    input_string = "${AWS::Region} ${Foo} ${!BASH_VAR} ${LocalA}"

    result = functions.sub_l(template, [input_string, var_map])

    assert "us-east-1" in result, "Should render aws pseudo vars."

    assert "bar" in result, "Should render parameters."

    assert "${BASH_VAR}" in result, "Should allow escaping variables."

    assert "TestA" in result, "Should render local variables."

    test_string = "SomeString"

    result = functions.sub_l(template, [test_string, var_map])

    assert result == test_string


def test_transform(fake_t):
    with pytest.raises(TypeError) as e:
        result = functions.transform(fake_t, [])

    assert "must be a Dict, not list." in str(e)

    with pytest.raises(KeyError) as e:
        result = functions.transform(fake_t, {})

    assert "a Name and Parameters." in str(e)

    transform = {"Name": "TestName", "Parameters": "TestParameters"}

    result = functions.transform(fake_t, transform)

    assert result == "TestName"


def test_ref():
    template = {"Parameters": {"foo": {"Value": "bar"}}, "Resources": {}}

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

    with pytest.raises(Exception) as ex:
        result = functions.ref(template, "SomeResource")

    assert "not a valid Resource" in str(ex)

    fake = "AWS::FakeVar"

    with pytest.raises(ValueError) as e:
        functions.ref(template, fake)

    assert f"Unrecognized AWS Pseduo variable: {fake!r}." in str(e.value)


def test_ref_resource():
    template = {"Resources": {"Foo": {}}}

    add_metadata(template, Template.Region)

    template = Template(template)

    result = functions.ref(template, "Foo")

    assert result == "Foo"
