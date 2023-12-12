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
