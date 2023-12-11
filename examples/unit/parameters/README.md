
# What does this example cover?

One of the features that lead me to adopting Cloud Radar was it's support for rendering intrinsic functions in a CloudFormation template, based on supplied parameters. As part of this Cloud Radar can validate that mandatory parameters are provided, and that all parameters are valid based on any defined [constraints](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#parameters-section-structure-properties).


This supports all the types of CloudFormation parameters:
* [String & Number](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#parameters-section-structure-properties)
* [AWS-specific](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#aws-specific-parameter-types)
* [SSM Parameter Types](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#aws-ssm-parameter-types)


You can use this feature to validate that any parameter configuration files are valid, and also use assertions to confirm that invalid values would be rejected. Parameters can either be supplied as a `dict` of Key/Value pairs, or loaded from configuration files. At this point the [CodePipeline artifact](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/cloudformation/deploy/index.html#supported-json-syntax) and [CloudFormation CLI](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/cloudformation/create-stack.html) formats can be loaded in from files.

The complete set of files for these examples are in this directory.

# Supplying Parameters

As noted above, parameter values can be supplied in a few different ways.

Inline:
```python
        template.create_stack(params={
            "MyBucket": "bad-ssm-path-$*£&@*"
        })
```

From configuration files (this example uses a path relative to the test case file):
```python
    config_path = Path(__file__).parent / "invalid_params_regex.cf.json"

    template.create_stack(parameters_file=config_path)
```

## Configuration File Formats
Examples of the two configuration formats are shown below.

CodePipeline:
```json
{
    "Parameters": {
        "Password": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXZY"
    }
}
```

CloudFormation CLI:
```json
[
    {
        "ParameterKey": "Password",
        "ParameterValue": "Abhd%k*"
    }
]
```


## Validating Parameters

A test that creates a stack with a set of parameters and does not raise a `ValueError` of any sort means the parameters have passed the validation constraints the template defined. You can then assert that properties in the "created" resources match expectations.

```python
def test_valid_params(template: Template):
  config_path = Path(__file__).parent / "valid_params.json"

  stack = template.create_stack(parameters_file=config_path)

  # No error at this point means that validation rules have
  # passed, go on to check the resource properties
  user_resource = stack.get_resource("CFNUser")
  login_profile_props = user_resource.get_property_value("LoginProfile")
  assert login_profile_props["Password"] == "aSuperSecurePassword"
```

You can validate that a parameter fails validation with a specific error. When building this up, it is sometimes easier to assert that it just raises a `ValueError` then output the error message so that the test can be updated to ensure the expected validation error is being encountered instead of a different one.

```python
def test_invalid_params(template: Template):
  config = load_config("invalid_params.json")

  with pytest.raises(
    ValueError,
    match=(
      "Value abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXZY is longer "
      "than the maximum length for parameter Password"
    ),
  ):
    template.create_stack(config["Parameters"])
```

## SSM Parameter Types

As well as validating that the SSM parameter key supplied matches the pattern for what an SSM parameter key should look like, Cloud Radar will substitute in values. The substitution of SSM parameters is also supported through [Dynamic References](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html).

The example template in the ssm directory includes this as one of the parameters for the template:
```yaml
Parameters:
  MyBucket:
    Type: 'AWS::SSM::Parameter::Value<String>'
    Description: The bucket name where all the data will be put into.
    Default: /my_parameters/bucket/name
```

Any place that this is included in a `!Ref` or a `!Sub` will have a value substituted in correctly, just like for other parameter types. This requires that when you define your `Template` in your test case that you include values that should be returned when SSM keys are referenced.

```python
    template_path = Path(__file__).parent / "SSM_Parameter_example.yaml"

    return Template.from_yaml(
        template_path.resolve(),
        dynamic_references={
            "ssm": {
                "/my_parameters/database/name": "my-great-database",
                "/my_parameters/bucket/name": "my-great-s3-bucket",
            }
        },
    )
```


If a parameter key is used which was not defined with the template, then a Key Error will be raised. You can test that unexpected parameters result in an error like this:

```python
    with pytest.raises(
        KeyError,
        match="Key /an/ssm/key/that/does/not/exist not included in dynamic references configuration for service ssm"
    ):
        template.create_stack(params={
            "MyBucket": "/an/ssm/key/that/does/not/exist"
        })
```
