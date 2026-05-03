"""Tests for the AWS::LanguageExtensions Fn::ToJsonString intrinsic.

AWS references:
https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/intrinsic-function-reference-ToJsonString.html
https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/transform-aws-languageextensions.html
"""

from cloud_radar.cf.unit._template import Template


def test_object_to_json_string():
    """Based on the AWS object example using a nested Ref."""

    template = Template(
        {
            "Transform": "AWS::LanguageExtensions",
            "Parameters": {"ParameterName": {"Type": "String"}},
            "Outputs": {
                "JsonString": {
                    "Value": {
                        "Fn::ToJsonString": {
                            "key1": "value1",
                            "key2": {"Ref": "ParameterName"},
                        }
                    }
                }
            },
        }
    )

    stack = template.create_stack(params={"ParameterName": "resolvedValue"})

    stack.get_output("JsonString").assert_value_is(
        '{"key1":"value1","key2":"resolvedValue"}'
    )


def test_array_to_json_string():
    """Uses the AWS array form, with the expected JSON inferred from the input.

    The AWS page's rendered output for the array example appears inconsistent
    with its input, so this test follows the documented behavior: an array
    should be converted to the corresponding JSON string after nested
    intrinsics are resolved.
    """

    template = Template(
        {
            "Transform": "AWS::LanguageExtensions",
            "Parameters": {"ParameterName": {"Type": "String"}},
            "Outputs": {
                "JsonString": {
                    "Value": {
                        "Fn::ToJsonString": [
                            {"key1": "value1"},
                            {"key2": {"Ref": "ParameterName"}},
                        ]
                    }
                }
            },
        }
    )

    stack = template.create_stack(params={"ParameterName": "resolvedValue"})

    stack.get_output("JsonString").assert_value_is(
        '[{"key1":"value1"},{"key2":"resolvedValue"}]'
    )
