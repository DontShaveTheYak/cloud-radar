import re
from pathlib import Path
from typing import Any, Dict, Union

from cfn_tools import dump_yaml, load_yaml  # type: ignore

import yaml


class Template:
    """Loads a Cloudformation template file so that it's parameters
    and conditions can be rendered into their final form for testing.
    """

    def __init__(self, template_path: Union[str, Path]) -> None:
        """Loads a Cloudformation template from a file and saves
        it as a dictionary.

        Args:
            template_path (Union[str, Path]): The path to the template.
        """

        template_path = Path(template_path)

        with open(template_path) as f:
            raw = f.read()

        self.raw: str = raw
        self.template: dict = self.load()

    def load(self) -> dict:

        template = load_yaml(self.raw)

        template = dump_yaml(template)

        template = yaml.load(template)

        return template

    def render(self, params: Dict[str, str] = None, region: str = "us-east-1") -> dict:
        """Solves all conditionals, references and pseudo variables using
        the passed in parameters. After rendering the template all resources
        that wouldn't get deployed because of a condtion statement are removed.

        Args:
            params (dict, optional): Parameter names and values to be used when rendering.
            region (str, optional): The region is used for the AWS::Region pseudo variable. Defaults to "us-east-1".

        Returns:
            dict: The rendered template.
        """  # noqa: B950

        self.region = region

        self.template = self.load()
        self.set_parameters(params)

        self.resolve_values(self.template)

        if "Resources" in self.template:
            resources = self.template["Resources"]
            for r_name, r_value in list(resources.items()):
                if "Condition" in r_value:
                    condition = self.template["Conditions"][r_value["Condition"]]

                    if not condition:
                        del self.template["Resources"][r_name]
                        continue

        return self.template

    def r_if(self, function: list) -> Any:
        """Solves AWS If intrinsic functions.

        Args:
            function (list): The condition, true value and false value.

        Returns:
            Any: The return value could be another intrinsic function, boolean or string.
        """

        condition = function[0]

        if not isinstance(condition, bool):
            condition = self.template["Conditions"][condition]

        if condition:
            resolved = function[1]
        else:
            resolved = function[2]

        return resolved

    def r_equals(self, function: list) -> bool:
        """Solves AWS Equals intrinsic functions.

        Args:
            function (list): A list with two items to be compared.

        Returns:
            bool: Returns True if the items are equal and false other wise.
        """

        return function[0] == function[1]

    def r_sub(self, function: str) -> str:
        """Solves AWS Sub intrinsic functions.

        Args:
            function (str): A string with ${} parameters or resources referenced in the template.

        Returns:
            str: Returns the rendered string.
        """  # noqa: B950

        def replace_var(m):
            var = m.group(2)

            if "AWS::" in var:
                # return var.replace('AWS::', '')
                return self.region

            return self.template["Parameters"][var]["Value"]

        reVar = r"(?!\$\{\!)\$(\w+|\{([^}]*)\})"

        if re.match(reVar, function):
            return re.sub(reVar, replace_var, function).replace("${!", "${")

        return function.replace("${!", "${")

    def resolve_values(self, data: Any) -> Any:
        """Recurses through a Cloudformation template. Solving all
        references and variables along the way.

        Args:
            data (Any): Could be a dict, list, str or int.

        Returns:
            Any: Return the rendered data structure.
        """

        if isinstance(data, dict):
            for key, value in data.items():

                if key == "Ref":
                    if value in self.template["Parameters"]:
                        return self.template["Parameters"][value]["Value"]
                    else:
                        return value

                value = self.resolve_values(value)

                if key == "Fn::Equals":
                    return self.r_equals(value)

                if key == "Fn::If":
                    return self.r_if(value)

                if key == "Fn::Sub":
                    return self.r_sub(value)

                data[key] = self.resolve_values(value)
            return data
        elif isinstance(data, list):
            return [self.resolve_values(item) for item in data]
        else:
            return data

    def set_parameters(self, parameters: Union[Dict[str, str], None] = None) -> None:
        """Sets the parameters for a template using the provided parameters or
        by using the default value of that parameter.

        Args:
            parameters (Union[dict, None ], optional): The parameters names and values. Defaults to None.

        Raises:
            Exception: Raises an Exeption if parameter is missing a default and a value is not provided.
        """  # noqa: B950

        if parameters is None:
            parameters = {}

        if "Parameters" not in self.template:
            return

        t_params = self.template["Parameters"]

        for p_name, p_value in t_params.items():
            if p_name in parameters:
                t_params[p_name]["Value"] = parameters[p_name]
                continue

            if "Default" not in p_value:
                raise Exception(
                    "Must provide values for parameters that dont have default"
                )

            t_params[p_name]["Value"] = p_value["Default"]
