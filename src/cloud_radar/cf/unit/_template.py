from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Generator, Optional, Tuple, Union

import yaml  # noqa: I100
from cfn_tools import dump_yaml, load_yaml  # type: ignore  # noqa: I100, I201

from . import functions
from ._stack import Stack

IntrinsicFunc = Callable[["Template", Any], Any]


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

    def __init__(
        self, template: Dict[str, Any], imports: Optional[Dict[str, str]] = None
    ) -> None:
        """Loads a Cloudformation template from a file and saves
        it as a dictionary.

        Args:
            template (Dict): The Cloudformation template as a dictionary.
            imports (Optional[Dict[str, str]], optional): Values this template plans
            to import from other stacks exports. Defaults to None.

        Raises:
            TypeError: If template is not a dictionary.
            TypeError: If imports is not a dictionary.
        """

        if imports is None:
            imports = {}

        if not isinstance(template, dict):
            raise TypeError(
                f"Template should be a dict, not {type(template).__name__}."
            )

        if not isinstance(imports, dict):
            raise TypeError(f"Imports should be a dict, not {type(imports).__name__}.")

        self.raw: str = yaml.dump(template)
        self.template = template
        self.Region = Template.Region
        self.imports = imports

    @classmethod
    def from_yaml(
        cls, template_path: Union[str, Path], imports: Optional[Dict[str, str]] = None
    ) -> Template:
        """Loads a Cloudformation template from file.

        Args:
            template_path (Union[str, Path]): The path to the template.
            imports (Optional[Dict[str, str]], optional): Values this template plans
            to import from other stacks exports. Defaults to None.

        Returns:
            Template: A Template object ready for testing.
        """

        with open(template_path) as f:
            raw = f.read()

        tmp_yaml = load_yaml(raw)

        tmp_str = dump_yaml(tmp_yaml)

        template = yaml.load(tmp_str, Loader=yaml.FullLoader)

        return cls(template, imports)

    def render(
        self, params: Optional[Dict[str, str]] = None, region: Optional[str] = None
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

        self.template = self.render_all_sections(self.template)

        self.template = self.remove_condtional_resources(self.template)

        return self.template

    def render_all_sections(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Solves all conditionals, references and pseudo variables for all sections"""
        if "Conditions" in template:
            template["Conditions"] = self.resolve_values(
                template["Conditions"],
                functions.ALL_FUNCTIONS,
            )

        template_sections = ["Resources", "Outputs"]

        for section in template_sections:
            if section not in template:
                continue

            for r_name, r_value in get_section_items(template, section):
                if is_conditional(r_value):
                    condition_value = get_condition_value(
                        r_value["Condition"], template["Conditions"]
                    )

                    if not condition_value:
                        continue

                template[section][r_name] = self.resolve_values(
                    r_value,
                    functions.ALL_FUNCTIONS,
                )

        return template

    def remove_condtional_resources(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Removes all resources that have a condition that evaluates to False."""

        # These are sections that can have conditional resources
        conditional_sections = ["Resources", "Outputs"]

        for section in conditional_sections:
            if section not in template:
                continue

            resources = template[section]

            for r_name, r_value in list(resources.items()):
                if not is_conditional(r_value):
                    continue

                condition_value = get_condition_value(
                    r_value["Condition"], template["Conditions"]
                )

                if not condition_value:
                    del template[section][r_name]
                    continue

        return template

    def create_stack(
        self, params: Optional[Dict[str, str]] = None, region: Optional[str] = None
    ):
        if region:
            self.Region = region

        self.render(params)

        stack = Stack(self.template)

        return stack

    def resolve_values(
        self,
        data: Any,
        allowed_func: functions.Dispatch,
    ) -> Any:
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
                    return functions.ref(self, value)

                # This takes care of keys that not intrinsic functions,
                #  except for the condition func
                if "Fn::" not in key and key != "Condition":
                    data[key] = self.resolve_values(
                        value,
                        allowed_func,
                    )
                    continue

                # Takes care of the tricky 'Condition' key
                if key == "Condition":
                    # The real fix is to not resolve every key/value in the entire
                    # cloudformation template. We should only attempt to resolve what is needed,
                    # like outputs and resource properties.
                    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html

                    if "Properties" in data or "Value" in data:
                        continue

                    # If it's an intrinsic func
                    if is_condition_func(value):
                        return functions.condition(self, value)

                    # Normal key like in an IAM role
                    data[key] = self.resolve_values(
                        value,
                        allowed_func,
                    )
                    continue

                if key not in allowed_func:
                    raise ValueError(f"{key} with value ({value}) not allowed here")

                value = self.resolve_values(
                    value,
                    functions.ALLOWED_FUNCTIONS[key],
                )

                return allowed_func[key](self, value)

            return data
        elif isinstance(data, list):
            return [
                self.resolve_values(
                    item,
                    allowed_func,
                )
                for item in data
            ]
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


# All the other Cloudformation intrinsic functions start with `Fn:` but for some reason
# the Condition function does not. This can be problem because
#  `Condition` is a valid key in an IAM policy but its value is always a Map.
def is_condition_func(value: Any) -> bool:
    """Checks if the 'Condition' key is a instrinsic function.

    Args:
        value (Any): The value of the 'Condition' key.

    Returns:
        bool: True if we think this `Condition` key is an instrinsic function.
    """
    if isinstance(value, str):
        return True

    return False


# Loop through a dictionary yielding the key and value
def iter_dict(data: dict) -> Generator[Tuple[str, Any], None, None]:
    for key, value in data.items():
        yield key, value


# return iter_dict for a given key in a dictionary
def get_section_items(
    data: dict, section: str
) -> Generator[Tuple[str, Any], None, None]:
    if section not in data:
        return iter_dict({})

    return iter_dict(data[section])


# Check if a dictionary has a key "Condition"
def is_conditional(data: dict) -> bool:
    if "Condition" in data:
        return True

    return False


# Return the conditional value of a resouce
def get_condition_value(condition_name: str, conditions: Dict[str, bool]) -> bool:
    return conditions[condition_name]
