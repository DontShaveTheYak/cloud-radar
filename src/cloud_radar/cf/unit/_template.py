from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Union

from cfn_tools import dump_yaml, load_yaml  # type: ignore

import yaml


class Template:
    """Loads a Cloudformation template file so that it's parameters
    and conditions can be rendered into their final form for testing.
    """

    AccountId: str = "5" * 12
    NotificationARNs: list = []
    NoValue: str = ""  # Not yet implemented
    Partition: str = "aws"  # Other regions not implemented
    Region: str = "us-east-1"
    StackId: str = ""  # Not yet implemented
    StackName: str = ""  # Not yet implemented
    URLSuffix: str = "amazonaws.com"  # Other regions not implemented

    def __init__(self, template: Dict[str, Any]) -> None:
        """Loads a Cloudformation template from a file and saves
        it as a dictionary.

        Args:
            template (Dict): The Cloudformation template as a dictionary.

        Raises:
            TypeError: If template is not a dictionary.
        """

        if not isinstance(template, dict):
            raise TypeError(f"Template should be dict not {type(template).__name__}.")

        self.raw: str = yaml.dump(template)
        self.template = template
        self.Region = Template.Region

    @classmethod
    def from_yaml(cls, template_path: Union[str, Path]) -> Template:

        with open(template_path) as f:
            raw = f.read()

        tmp_yaml = load_yaml(raw)

        tmp_str = dump_yaml(tmp_yaml)

        template = yaml.load(tmp_str, Loader=yaml.FullLoader)

        return cls(template)

    def render(
        self, params: Dict[str, str] = None, region: Union[str, None] = None
    ) -> dict:
        """Solves all conditionals, references and pseudo variables using
        the passed in parameters. After rendering the template all resources
        that wouldn't get deployed because of a condtion statement are removed.

        Args:
            params (dict, optional): Parameter names and values to be used when rendering.
            region (str, optional): The region is used for the AWS::Region pseudo variable. Defaults to "us-east-1".

        Returns:
            dict: The rendered template.
        """  # noqa: B950

        if region:
            self.Region = region

        self.template = yaml.load(self.raw, Loader=yaml.FullLoader)
        self.set_parameters(params)

        add_metadata(self.template, self.Region)

        self.resolve_values(self.template)

        resources = self.template["Resources"]
        for r_name, r_value in list(resources.items()):
            if "Condition" in r_value:
                condition = self.template["Conditions"][r_value["Condition"]]

                if not condition:
                    del self.template["Resources"][r_name]
                    continue

        return self.template

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
                    return r_ref(self.template, value)

                value = self.resolve_values(value)

                if key == "Fn::Equals":
                    return r_equals(value)

                if key == "Fn::If":
                    return r_if(self.template, value)

                if key == "Fn::Sub":
                    return r_sub(self.template, value)

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
            parameters (Union[Dict[str, str], None], optional): The parameters names and values. Defaults to None.

        Raises:
            ValueError: If you supply parameters for a template that doesn't have any.
            ValueError: If you pass parameters that are not in this template.
            ValueError: If Template Parameter is missing a default and a value is not provided.
        """  # noqa: B950

        if parameters is None:
            parameters = {}

        if "Parameters" not in self.template:
            if parameters:
                raise ValueError(
                    "You supplied parameters for a template that doesn't have any."
                )
            return

        t_params: dict = self.template["Parameters"]

        if set(parameters) - set(t_params):
            raise ValueError("You passed a Parameter that was not in the Template.")

        for p_name, p_value in t_params.items():
            if p_name in parameters:
                t_params[p_name]["Value"] = parameters[p_name]
                continue

            if "Default" not in p_value:
                raise ValueError(
                    "Must provide values for parameters that don't have a default value."
                )

            t_params[p_name]["Value"] = p_value["Default"]


def add_metadata(template: Dict, region: str) -> None:
    """This functions adds the current region to the template
    as metadate because we can't treat Region like a normal pseduo
    variables because we don't want to update the class var for every run.

    Args:
        template (Dict): The template you want to update.
        region (str): The region that template will be tested with.
    """

    metadata = {"Cloud-Radar": {"Region": region}}

    if "Metadata" not in template:
        template["Metadata"] = {}

    template["Metadata"].update(metadata)


def r_equals(function: list) -> bool:
    """Solves AWS Equals intrinsic functions.

    Args:
        function (list): A list with two items to be compared.

    Returns:
        bool: Returns True if the items are equal, else False.
    """

    return function[0] == function[1]


def r_if(template: Dict, function: list) -> Any:
    """Solves AWS If intrinsic functions.

    Args:
        function (list): The condition, true value and false value.

    Returns:
        Any: The return value could be another intrinsic function, boolean or string.
    """

    condition = function[0]

    if type(condition) is not str:
        raise Exception(f"AWS Condition should be str not {type(condition).__name__}.")

    condition = template["Conditions"][condition]

    if condition:
        return function[1]

    return function[2]


def r_ref(template: Dict, var_name: str) -> Union[str, int, float, list]:
    """Takes the name of a parameter, resource or pseudo variable and finds the value for it.

    Args:
        template (Dict): The Cloudformation template.
        var_name (str): The name of the parameter, resource or pseudo variable.

    Raises:
        ValueError: If the supplied pseudo variable doesn't exist.

    Returns:
        Union[str, int, float, list]: The value of the parameter, resource or pseudo variable.
    """

    if "AWS::" in var_name:
        pseudo = var_name.replace("AWS::", "")

        # Can't treat region like a normal pseduo because
        # we don't want to update the class var for every run.
        if pseudo == "Region":
            return template["Metadata"]["Cloud-Radar"]["Region"]
        try:
            return getattr(Template, pseudo)
        except AttributeError:
            raise ValueError(f"Unrecognized AWS Pseduo variable: '{var_name}'.")

    if var_name in template["Parameters"]:
        return template["Parameters"][var_name]["Value"]
    else:
        return var_name


def r_sub(template: Dict, function: str) -> str:
    """Solves AWS Sub intrinsic functions.

    Args:
        function (str): A string with ${} parameters or resources referenced in the template.

    Returns:
        str: Returns the rendered string.
    """  # noqa: B950

    def replace_var(m):
        var = m.group(2)
        return r_ref(template, var)

    reVar = r"(?!\$\{\!)\$(\w+|\{([^}]*)\})"

    if re.search(reVar, function):
        return re.sub(reVar, replace_var, function).replace("${!", "${")

    return function.replace("${!", "${")
