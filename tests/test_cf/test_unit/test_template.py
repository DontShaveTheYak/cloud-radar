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

    with pytest.raises(TypeError) as e:
        Template({}, {}, "")  # type: ignore

    assert "Dynamic References should be a dict, not str." in str(e)

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
        "Parameters": {"testParam": {"Type": "String", "Default": "Test Value"}},
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
        "Parameters": {"testParam": {"Type": "String", "Default": "Test Value"}},
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
        "Parameters": {"testParam": {"Type": "String", "Default": "Test Value"}},
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
        "Parameters": {"Test": {"Type": "String", "Value": "test"}},
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
        "Parameters": {"Test": {"Type": "String", "Value": "test"}},
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

    template.template = {
        "Parameters": {
            "Test": {
                "Type": "String",
            }
        }
    }

    with pytest.raises(ValueError) as e:
        template.set_parameters()

    assert "Must provide values for parameters that don't have a default value." in str(
        e.value
    ), "Should throw correct exception."

    template.set_parameters({"Test": "value"})

    assert {"Test": {"Type": "String", "Value": "value"}} == template.template[
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


def test_set_params_string_allowed_values():
    t = {
        "Parameters": {
            "InstanceTypeParameter": {
                "Type": "String",
                "Default": "t2.micro",
                "AllowedValues": ["t2.micro", "m1.small", "m1.large"],
                "Description": (
                    "Enter t2.micro, m1.small, or m1.large. Default is t2.micro."
                ),
            }
        }
    }
    template = Template(t)

    # Test that supplying one of the allowed values works
    template.set_parameters({"InstanceTypeParameter": "m1.small"})

    actual_value = template.template["Parameters"]["InstanceTypeParameter"]
    assert (
        "m1.small" == actual_value["Value"]
    ), "Should set the value to what we pass in."

    # Test that supplying a value not in the allowed values fails
    with pytest.raises(
        ValueError,
        match="Value m5.large not in allowed values for parameter InstanceTypeParameter",
    ):
        template.set_parameters({"InstanceTypeParameter": "m5.large"})


def test_set_params_string_list_allowed_values():
    t = {
        "Parameters": {
            "InstanceTypeParameter": {
                "Type": "CommaDelimitedList",
                "Default": "t2.micro",
                "AllowedValues": ["t2.micro", "m1.small", "m1.large"],
                "Description": (
                    "Enter t2.micro, m1.small, or m1.large. Default is t2.micro."
                ),
            }
        }
    }
    template = Template(t)

    # Test that supplying one of the allowed values works
    template.set_parameters({"InstanceTypeParameter": "m1.small"})

    actual_value = template.template["Parameters"]["InstanceTypeParameter"]
    assert (
        "m1.small" == actual_value["Value"]
    ), "Should set the value to what we pass in."

    # Test that supplying a list of valid values works
    template.set_parameters({"InstanceTypeParameter": "m1.small,t2.micro"})

    actual_value = template.template["Parameters"]["InstanceTypeParameter"]
    assert (
        "m1.small,t2.micro" == actual_value["Value"]
    ), "Should set the value to what we pass in."

    # Test that supplying a value not in the allowed values fails
    with pytest.raises(
        ValueError,
        match="Value m5.large not in allowed values for parameter InstanceTypeParameter",
    ):
        template.set_parameters({"InstanceTypeParameter": "m1.small,m5.large,t2.micro"})


def test_set_params_string_length_allowed_pattern():
    t = {
        "Parameters": {
            "DBPwd": {
                "NoEcho": "true",
                "Description": "The database admin account password",
                "Type": "String",
                "MinLength": "5",
                "MaxLength": "21",
                "AllowedPattern": "^[a-zA-Z0-9]*$",
            }
        }
    }
    template = Template(t)

    # Test that supplying something that meets the criteria works
    template.set_parameters({"DBPwd": "m1Small"})

    actual_value = template.template["Parameters"]["DBPwd"]
    assert (
        "m1Small" == actual_value["Value"]
    ), "Should set the value to what we pass in."

    # Test that supplying something too short is rejected
    with pytest.raises(
        ValueError,
        match="Value m1s is shorter than the minimum length for parameter DBPwd",
    ):
        template.set_parameters({"DBPwd": "m1s"})

    # Test that supplying something too long is rejected
    with pytest.raises(
        ValueError,
        match=(
            "Value m1s921234512345naodinvaoinvoiaenfio is longer than the "
            "maximum length for parameter DBPwd"
        ),
    ):
        template.set_parameters({"DBPwd": "m1s921234512345naodinvaoinvoiaenfio"})

    # Test that supplying something that does not match the pattern is rejected
    with pytest.raises(
        ValueError,
        match=(
            "Value my-super-password does not match the AllowedPattern "
            "for parameter DBPwd"
        ),
    ):
        template.set_parameters({"DBPwd": "my-super-password"})


def test_set_params_number_min_max():
    t = {
        "Parameters": {
            "DBPort": {
                "Default": "3306",
                "Description": "TCP/IP port for the database",
                "Type": "Number",
                "MinValue": "1150",
                "MaxValue": "65535",
            },
        }
    }
    template = Template(t)

    # Test that supplying something that meets the criteria works
    template.set_parameters({"DBPort": "5432"})

    actual_value = template.template["Parameters"]["DBPort"]
    assert "5432" == actual_value["Value"], "Should set the value to what we pass in."

    # Test the supplying something below the min value is rejected
    with pytest.raises(
        ValueError,
        match=("Value 1149 is below the minimum value " "for parameter DBPort"),
    ):
        template.set_parameters({"DBPort": "1149"})

    # Test the supplying something above the max value is rejected
    with pytest.raises(
        ValueError,
        match=("Value 65536 is above the maximum value " "for parameter DBPort"),
    ):
        template.set_parameters({"DBPort": "65536"})


def test_set_params_list_number_min_max():
    t = {
        "Parameters": {
            "ASGCapacity": {
                "Type": "List<Number>",
                "Description": (
                    "Min, Desired & Max capacity of Autoscaling Group "
                    "separated with comma."
                ),
                "MinValue": "2",
                "MaxValue": "10",
            }
        }
    }
    template = Template(t)

    # Test that supplying a single value that meets the criteria works
    template.set_parameters({"ASGCapacity": "2"})

    actual_value = template.template["Parameters"]["ASGCapacity"]
    assert "2" == actual_value["Value"], "Should set the value to what we pass in."

    # Test that supplying a list of valid values works
    template.set_parameters({"ASGCapacity": "2, 2, 10"})

    actual_value = template.template["Parameters"]["ASGCapacity"]
    assert (
        "2, 2, 10" == actual_value["Value"]
    ), "Should set the value to what we pass in."

    # Test the supplying something below the min value is rejected
    with pytest.raises(
        ValueError,
        match=("Value 1 is below the minimum value for parameter ASGCapacity"),
    ):
        template.set_parameters({"ASGCapacity": "2, 1, 10"})

    # Test the supplying something above the max value is rejected
    with pytest.raises(
        ValueError,
        match=("Value 11 is above the maximum value for parameter ASGCapacity"),
    ):
        template.set_parameters({"ASGCapacity": "2, 5, 11"})


@pytest.mark.parametrize(
    "type,valid_input,invalid_input,fail_message_value,fail_message_type",
    [
        (
            "AWS::EC2::AvailabilityZone::Name",
            "us-east-1a",
            "xx-west-1c",
            "xx-west-1c",
            "AWS::EC2::AvailabilityZone::Name",
        ),
        (
            "AWS::EC2::Image::Id",
            "ami-0ff8a91507f77f867",
            "mygreatimage",
            "mygreatimage",
            "AWS::EC2::Image::Id",
        ),
        (
            "AWS::EC2::Instance::Id",
            "i-1e731a32",
            "ke-1e731a32",
            "ke-1e731a32",
            "AWS::EC2::Instance::Id",
        ),
        (
            "AWS::EC2::KeyPair::KeyName",
            "my-nv-keypair",
            "t" * 256,
            "t" * 256,
            "AWS::EC2::KeyPair::KeyName",
        ),
        (
            "AWS::EC2::SecurityGroup::GroupName",
            "my-sg-abc",
            "'sg",
            "'sg",
            "AWS::EC2::SecurityGroup::GroupName",
        ),
        (
            "AWS::EC2::SecurityGroup::Id",
            "sg-a123fd85",
            "ke-1e731a32",
            "ke-1e731a32",
            "AWS::EC2::SecurityGroup::Id",
        ),
        (
            "AWS::EC2::Subnet::Id",
            "subnet-123a351e",
            "sunbet-123a351e",
            "sunbet-123a351e",
            "AWS::EC2::Subnet::Id",
        ),
        (
            "AWS::EC2::Volume::Id",
            "vol-3cdd3f56",
            "vl-3cdd3f56",
            "vl-3cdd3f56",
            "AWS::EC2::Volume::Id",
        ),
        (
            "AWS::EC2::Volume::Id",
            "vol-3cdd3f56ae231cef5",
            "vol-3cdd3f56ae231cef5a",
            "vol-3cdd3f56ae231cef5a",
            "AWS::EC2::Volume::Id",
        ),
        (
            "AWS::EC2::VPC::Id",
            "vpc-a123baa3",
            "vpc-a123-baa3",
            "vpc-a123-baa3",
            "AWS::EC2::VPC::Id",
        ),
        (
            "AWS::Route53::HostedZone::Id",
            "Z23YXV4OVPL04A",
            "Z23Y-XV4O-VPL04A",
            "Z23Y-XV4O-VPL04A",
            "AWS::Route53::HostedZone::Id",
        ),
        (
            "List<AWS::EC2::AvailabilityZone::Name>",
            "eu-west-1a, us-east-1b",
            "eu-west-1a, xx-west-1b",
            "xx-west-1b",
            "AWS::EC2::AvailabilityZone::Name",
        ),
        (
            "List<AWS::EC2::Image::Id>",
            "ami-0ff8a91507f77f867, ami-0a584ac55a7631c0c, ami-07d1ddc0a19021abb",
            "ami-0ff8a91507f77f867, ami-0a584ac55a7631c0c, mygreatimage",
            "mygreatimage",
            "AWS::EC2::Image::Id",
        ),
        (
            "List<AWS::EC2::Instance::Id>",
            "i-1e731a32, i-1e731a34, i-1e731a34213424fde, i-1234567890abcdef0",
            "i-1e731a32,i-1e731a34213424fdea",
            "i-1e731a34213424fdea",
            "AWS::EC2::Instance::Id",
        ),
        (
            "List<AWS::EC2::SecurityGroup::GroupName>",
            "my-sg-abc, my-sg-def, MySecurityGroup",
            "my-sg-abc, my-sg-def'",
            "my-sg-def'",
            "AWS::EC2::SecurityGroup::GroupName",
        ),
        (
            "List<AWS::EC2::SecurityGroup::Id>",
            "sg-a123fd85, sg-b456fd85, sg-903004f8",
            "sg-a123fd85, sg-b456fd85jgkfmd",
            "sg-b456fd85jgkfmd",
            "AWS::EC2::SecurityGroup::Id",
        ),
        (
            "List<AWS::EC2::Subnet::Id>",
            "subnet-123a351e, subnet-456b351e, subnet-5f46ec3b, subnet-9d4a7b6c",
            "subnet-123a351e, subnet-z456b351e",
            "subnet-z456b351e",
            "AWS::EC2::Subnet::Id",
        ),
        (
            "List<AWS::EC2::Volume::Id>",
            "vol-3cdd3f56, vol-4cdd3f56, vol-049df61146c4d7901",
            "vol-3cdd3f56, vol-4cdd3f56, vl-3cdd3f56",
            "vl-3cdd3f56",
            "AWS::EC2::Volume::Id",
        ),
        (
            "List<AWS::EC2::VPC::Id>",
            "vpc-a123baa3, vpc-b456baa3, vpc-010e1791024eb0af9",
            "vpc-a123baa3, vapc-b456baa3",
            "vapc-b456baa3",
            "AWS::EC2::VPC::Id",
        ),
        (
            "List<AWS::Route53::HostedZone::Id>",
            "Z23YXV4OVPL04A, Z23YXV4OVPL04B, Z7HUB22UULQXV",
            "Z23YXV4OVPL04B, Z23Y-XV4O-VPL04A",
            "Z23Y-XV4O-VPL04A",
            "AWS::Route53::HostedZone::Id",
        ),
    ],
)
def test_set_params_aws_type(
    type: str,
    valid_input: str,
    invalid_input: str,
    fail_message_value: str,
    fail_message_type: str,
):
    t = {
        "Parameters": {
            "TargetAvailabilityZones": {
                "Type": type,
                "Description": ("The AZ(s) we are deploying to"),
            }
        }
    }
    template = Template(t)

    # Test that supplying a list of valid AZ values works
    template.set_parameters({"TargetAvailabilityZones": valid_input})

    actual_value = template.template["Parameters"]["TargetAvailabilityZones"]
    assert (
        valid_input == actual_value["Value"]
    ), "Should set the value to what we pass in."

    # Test the supplying an invalid AZ is rejected
    with pytest.raises(
        ValueError,
        match=(
            "Value " + fail_message_value + " does not match the expected pattern for "
            "parameter TargetAvailabilityZones and type " + fail_message_type
        ),
    ):
        template.set_parameters({"TargetAvailabilityZones": invalid_input})


@pytest.mark.parametrize("t", [{}, {"Metadata": {}}])
def test_metadata(t):
    region = "us-east-1"
    add_metadata(t, region=region)

    assert "Metadata" in t

    assert region == t["Metadata"]["Cloud-Radar"]["Region"]


def test_render_condition_keys():
    t = {
        "Parameters": {"testParam": {"Type": "String", "Default": "Test Value"}},
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


def test_resolve_dynamic_references():
    t = {
        "Resources": {
            "Foo": {
                "Type": "AWS::IAM::Policy",
                "Properties": {
                    "PolicyName": (
                        "mgt-{{resolve:ssm:/account/current/short_name}}"
                        "-launch-role-pol"
                    ),
                },
            },
            "Bar": {
                "Type": "AWS::IAM::Policy",
                "Properties": {
                    "PolicyName": {
                        "Fn::Sub": (
                            "mgt-{{resolve:ssm:/account/${AWS::AccountId}/short_name}}"
                            "-launch-role-pol"
                        )
                    },
                },
            },
            "TwoRefTest": {
                "Type": "AWS::IAM::Policy",
                "Properties": {
                    "PolicyName": {
                        "Fn::Sub": (
                            "mgt-{{resolve:ssm:/account/${AWS::AccountId}/short_name}}"
                            "-launch-{{resolve:ssm:/account/current/short_name}}-pol"
                        )
                    },
                },
            },
        },
    }

    dynamic_references = {
        "ssm": {
            "/account/current/short_name": "cld-rdr",
            "/account/555555555555/short_name": "cld-55-rdr",
        }
    }

    template = Template(t, dynamic_references=dynamic_references)

    result = template.render()

    # This item "just" resolves the SSM parameter
    foo_resource_props = result["Resources"]["Foo"]["Properties"]
    assert foo_resource_props["PolicyName"] == "mgt-cld-rdr-launch-role-pol"

    # This item resolves the SSM parameter after a substitution has been performed
    bar_resource_props = result["Resources"]["Bar"]["Properties"]
    assert bar_resource_props["PolicyName"] == "mgt-cld-55-rdr-launch-role-pol"

    # This item contains multiple resolved parameters
    two_resource_props = result["Resources"]["TwoRefTest"]["Properties"]
    assert two_resource_props["PolicyName"] == "mgt-cld-55-rdr-launch-cld-rdr-pol"


def test_resolve_all_types_dynamic_references():
    # This contains one of each type of dynamic references, with
    # the example resources coming from the documentation
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html
    t = {
        "Resources": {
            "MyRDSInstance": {
                "Type": "AWS::RDS::DBInstance",
                "Properties": {
                    "DBName": "MyRDSInstance",
                    "AllocatedStorage": "20",
                    "DBInstanceClass": "db.t2.micro",
                    "Engine": "mysql",
                    "MasterUsername": (
                        "{{resolve:secretsmanager:MyRDSSecret:SecretString:username}}"
                    ),
                    "MasterUserPassword": (
                        "{{resolve:secretsmanager:MyRDSSecret:SecretString:password}}"
                    ),
                },
            },
            "MyIAMUser": {
                "Type": "AWS::IAM::User",
                "Properties": {
                    "UserName": "MyUserName",
                    "LoginProfile": {
                        "Password": "{{resolve:ssm-secure:IAMUserPassword:10}}"
                    },
                },
            },
            "MyS3Bucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {"AccessControl": "{{resolve:ssm:S3AccessControl:2}}"},
            },
        }
    }

    dynamic_references = {
        "ssm": {"S3AccessControl:2": "private"},
        "ssm-secure": {"IAMUserPassword:10": "my-really-secure-iam-password"},
        "secretsmanager": {
            "MyRDSSecret:SecretString:username": "my-username",
            "MyRDSSecret:SecretString:password": "my-password",
        },
    }

    template = Template(t, dynamic_references=dynamic_references)
    result = template.render()

    rds_resource_props = result["Resources"]["MyRDSInstance"]["Properties"]
    assert rds_resource_props["MasterUsername"] == "my-username"
    assert rds_resource_props["MasterUserPassword"] == "my-password"

    iam_resource_props = result["Resources"]["MyIAMUser"]["Properties"]
    assert (
        iam_resource_props["LoginProfile"]["Password"]
        == "my-really-secure-iam-password"
    )

    s3_resource_props = result["Resources"]["MyS3Bucket"]["Properties"]
    assert s3_resource_props["AccessControl"] == "private"


def test_unknown_dynamic_references():
    t = {
        "Resources": {
            "Foo": {
                "Type": "AWS::IAM::Policy",
                "Properties": {
                    "PolicyName": (
                        "mgt-{{resolve:ssm:/account/current/short_name}}"
                        "-launch-role-pol"
                    ),
                },
            },
        },
    }

    # Case where there is no dynamic reference configuration
    template = Template(t)
    with pytest.raises(
        KeyError, match="Service ssm not included in dynamic references configuration"
    ):
        template.render()

    # Case where there is a dynamic reference configuration for the service,
    # but not the key
    template = Template(t, dynamic_references={"ssm": {"not/the/right/key": "dummy"}})
    with pytest.raises(
        KeyError,
        match=(
            "Key /account/current/short_name not"
            " included in dynamic references configuration"
            " for service ssm"
        ),
    ):
        template.render()
