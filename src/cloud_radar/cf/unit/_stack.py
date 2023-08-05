from collections import UserDict
from typing import Any, Dict

from ._condition import Condition
from ._output import Output
from ._parameter import Parameter
from ._resource import Resource


class Stack(UserDict):
    def __init__(self, rendered_template: Dict[str, Any]) -> None:
        super().__init__(rendered_template)

    def has_parameter(self, param_name: str):
        """Tests that a parameter is defined in the 'Parameters' section of the template.

        Args:
            param_name (str): The name of the parameter.
        """
        params = self.data.get("Parameters", {})

        assert param_name in params, f"Parameter '{param_name}' not found in template."

    def no_parameter(self, param_name: str):
        """Tests that a parameter is not defined in the 'Parameters' section of the template.

        Args:
            param_name (str): The name of the parameter.
        """
        params = self.data.get("Parameters", {})

        assert (
            param_name not in params
        ), f"Parameter '{param_name}' was found in template."

    def get_parameter(self, param_name: str):
        """Tests that a parameter is defined in the 'Parameters' section of the template and
        returns it.

        Args:
            param_name (str): The name of the parameter.
        """
        self.has_parameter(param_name)

        params = self.data["Parameters"]

        param_data = params[param_name]

        param = Parameter(param_name, param_data)

        return param

    def has_condition(self, condition_name: str):
        """Tests that a condition is defined in the 'Conditions' section of the template.

        Args:
            condition_name (str): The name of the condition.
        """
        conditions = self.data.get("Conditions", {})

        assert (
            condition_name in conditions
        ), f"Condition '{condition_name}' not found in template."

    def no_condition(self, condition_name: str):
        """Tests that a condition is not defined in the 'Conditions' section of the template.

        Args:
            condition_name (str): The name of the condition.
        """
        conditions = self.data.get("Conditions", {})

        assert (
            condition_name not in conditions
        ), f"Condition '{condition_name}' was found in template."

    def get_condition(self, condition_name: str):
        """Tests that a condition is defined in the 'Conditions' section of the template
        and returns it.

        Args:
            condition_name (str): The name of the condition.
        """
        self.has_condition(condition_name)

        conditions = self.data["Conditions"]

        condition_value = conditions[condition_name]

        condition = Condition(condition_name, condition_value)

        return condition

    def has_resource(self, resource_name: str):
        """Tests that a resource is defined in the 'Resources' section of the template.

        Args:
            resource_name (str): The name of the resource.
        """
        resources = self.data.get("Resources", {})

        assert (
            resource_name in resources
        ), f"Resource '{resource_name}' not found in template."

    def no_resource(self, resource_name: str):
        """Tests that a resource is not defined in the 'Resources' section of the template.

        Args:
            resource_name (str): The name of the resource.
        """
        resources = self.data.get("Resources", {})

        assert (
            resource_name not in resources
        ), f"Resource '{resource_name}' was found in template."

    def get_resource(self, resource_name: str):
        """Tests that a resource is defined in the 'Resources' section of the template
        and returns it.

        Args:
            resource_name (str): The name of the resource.
        """
        self.has_resource(resource_name)

        resources = self.data["Resources"]

        resource_data = resources[resource_name]

        resource = Resource(resource_name, resource_data)

        return resource

    def get_resources_of_type(self, resource_type: str):
        """
        Get all resources defined in the 'Resources' section of the
        template with a given type.

        This returns a dict of resource name to the resource.

        Args:
            resource_type (str): the cloudformation resource type to find
        """

        resources = self.data.get("Resources", {})
        return dict(
            filter(
                lambda item: item[1]["Type"] == resource_type,
                resources.items(),
            )
        )

    def has_output(self, output_name: str):
        """Tests that an output is defined in the 'Outputs' section of the template.

        Args:
            output_name (str): The name of the output.
        """
        outputs = self.data.get("Outputs", {})

        assert output_name in outputs, f"Output '{output_name}' not found in template."

    def no_output(self, output_name: str):
        """Tests that an output is not defined in the 'Outputs' section of the template.

        Args:
            output_name (str): The name of the output.
        """
        outputs = self.data["Outputs"]

        assert (
            output_name not in outputs
        ), f"Output '{output_name}' was found in template."

    def get_output(self, output_name: str):
        """Tests that an output is defined in the 'Outputs' section of the template
        and returns it.

        Args:
            output_name (str): The name of the output.
        """
        self.has_output(output_name)

        outputs = self.data["Outputs"]

        output_data = outputs[output_name]

        output = Output(output_name, output_data)

        return output

    def assert_resource_type_property_value_conventions(
        self, type_patterns: dict, fail_on_missing_type: bool = True
    ):
        """
        This method will perform assertions on all resources in the stack to check
        that a property or tag value matches a regex pattern.

        This is commonly used to ensure that resources match naming conventions. The
        test_naming_advanced.py example file shows how to use this.

        The type_patterns dict uses CloudFormation resource types as the keys,
        with the values being an object defining if it should be checked (default
        True), the pattern to compare against, and the details of the Property
        or Tag to get the value for.

        For a type which uses a property:
        {
            "AWS::S3::Bucket": {
                "Property": "BucketName",
                "Pattern": r"^[a-z0-9-]*-xx-west-3[a-z0-9-]*$",
            }
        }

        For a type which uses a tag:
        {
            "AWS::EFS::FileSystem": {
                "Tag": "Name",
                # This TagProperty is optional. The default is 'Tags',
                # but some resources use a different property name for
                # their tags.
                "TagProperty": "FileSystemTags",
                "Pattern": r"^[a-z0-9-]*-vol$",
            }
        }

        For a type which should not be checked:
        {
            "AWS::S3::BucketPolicy": {
                # The BucketPolicy type does not support custom names. If we do not
                # want to set fail_on_missing_type=False when we call the assertion
                # below then we need to include this type in the dict, and set it
                # not to be checked.
                # This approach ensures that types do not slip through unintentionally.
                "Check": False
            }
        }


        Args:
            type_patterns (dict): A dict with the key being the resource type,
                                  and the value an object, in one of the formats
                                  specified above.
            fail_on_missing_type (bool): If this is set to true, an assertion error
                                         will be thrown if the stack contains a
                                         resource of a type that is not defined in
                                         the type_patterns dict.
        """

        for resource_name in self.data.get("Resources", {}):
            resource_value = self.get_resource(resource_name)

            naming_convention = type_patterns.get(resource_value.get("Type"))
            resource_type = resource_value.get_type_value()

            assert naming_convention is not None or not fail_on_missing_type, (
                f"Resource '{resource_value.name}' has type '{resource_type}' "
                f"which is not included in the supplied type_patterns."
            )

            if naming_convention is not None and naming_convention.get("Check", True):
                # Only proceed further if this type is to be checked.
                # This might be set to False where a resource cannot have
                # a custom name

                assert "Pattern" in naming_convention, (
                    f"Naming convention definition for {resource_type} did not contain"
                    " a 'Pattern', and 'Check' was not set to False."
                )
                pattern = naming_convention["Pattern"]

                if "Property" in naming_convention:
                    # The name is held in a top level property
                    resource_value.assert_property_value_matches_pattern(
                        naming_convention["Property"], pattern
                    )
                elif "Tag" in naming_convention:
                    # The name is held in a tag. We can also look in the configuration
                    # for a custom tag property, as not all resources use Tag
                    resource_value.assert_tag_value_matches_pattern(
                        naming_convention["Tag"],
                        pattern,
                        naming_convention.get("TagProperty", "Tags"),
                    )
                else:
                    raise AssertionError(
                        (
                            f"Naming convention definition for {resource_type} did not "
                            f"contain one of 'Property' or 'Tag', and 'Check' was not "
                            "set to False."
                        )
                    )
