# What do these examples cover?

The two subdirectories here, `resources` and `template`, show the two types of "hooks" that are available for defining common checks.

The "hooks" functionality allows you to configure standardised tests once (for example through your `pytest` `conftest.py` file, possibly even using functions from an external library), and then each test stack you create will have your tests applied to them at the point the stack is rendered. In future it is planned to support a plugin system to discover these hooks through installed packages to simplify this configuration.

Hooks can be suppressed using CloudFormation MetaData (in a similar fashion to other tools like cfn-lint), at either the template or resource level. The expected format is as follows, where the items in the list are the function names of the configured hooks.

```
    Metadata:
      Cloud-Radar:
        ignore-hooks:
          - my_s3_encryption_hook
```

# Template Hooks

Template hooks are evaluated at the point that the CloudFormation template is loaded in to Cloud-Radar by calling `Template.from_yaml` function. These are designed for performing template level checks that do not depend on the template having any processing performed on it for parameter/condition resolution etc.

The types of scenarios this could be used for include:
* ensuring that all templates have some common parameters that are expected to be used for naming
* ensuring that all parameters have input validation configured

A basic example is included in the [template/test_hooks_template.py](./template/test_hooks_template.py) file.

## Defining a Hook

Template hooks are functions that take in a single parameter, `template`. These are expected to raise an error if their check does not pass.

```python
# Example hook that checks that the cloudformation template
# name for all parameters starts with a "p".
def my_parameter_prefix_checks(template: Template) -> None:
    # Get all the parameters
    parameters = template.template.get("Parameters", {})

    # Check them
    _object_prefix_check(parameters, "p")

def _object_prefix_check(items: List[str], expected_prefix: str):
    # Iterate through each parameter checking them
    for item in items:
        if not item.startswith(expected_prefix):
            raise ValueError(
                f"{item} does not follow the convention of starting with '{expected_prefix}'"
            )
```

The name of your function is used as the hook name in assertion messages and for the purposes of suppressions, so you should try to keep them unique within your code.

## Configuring a Hook

This type of hooks are set as a list of functions on the Template object.

```
Template.Hooks.template = [ my_parameter_prefix_checks ]
```

# Resource Hooks

Resource hooks are evaluated at the point of the stack being rendered by calling `template.create_stack`. These hooks are designed to be able to check aspects of the template *after* items like parameter substitution and conditions have been applied.

These are intended for much more in depth checks, specific to the type of a resource. The initial inception of this feature was to support naming convention checks, but equally can be expanded into the sorts of compliance tests that [CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html) is used for if you prefer to code rules in Python as opposed to the Guard DSL.

A basic example is included in the [resources/test_hooks_resources.py](./resources/test_hooks_resources.py) file.

## Defining a Hook

Resource hooks are functions that take in a single `context` parameter. This is a `ResourceHookContext` object that contains the following:

```
    logical_id: str
    resource_definition: Resource
    stack: Stack
    template: "Template"
```

These type of hooks are expected to raise an error if their check does not pass.

As a basic compliance type example, this hook verifies that the encryption property is present for an S3 resource.

```python
# Example hook that verifies  that all S3 bucket definitions
# have the "BucketEncryption" property set
def my_s3_encryption_hook(context: ResourceHookContext) -> None:
    # Use one of the built in functions to confirm the property exists
    context.resource_definition.assert_has_property("BucketEncryption")
```

This is configured as a hook against the S3 resource type by

```python
Template.Hooks.resources = {
    "AWS::S3::Bucket": [my_s3_naming_hook, my_s3_encryption_hook]
}

```

In this setup a dict is set with the AWS Resource type as the key, and a list of functions for the value.
