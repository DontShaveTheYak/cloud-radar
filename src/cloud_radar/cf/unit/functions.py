"""AWS Intrinsic functions.

This module contains the logic to solve both AWS Intrinsic
and Condition functions.
"""

import re
from typing import Any, Dict, TYPE_CHECKING, Union


if TYPE_CHECKING:
    from ._template import Template


def equals(function: list) -> bool:
    """Solves AWS Equals intrinsic functions.

    Args:
        function (list): A list with two items to be compared.

    Returns:
        bool: Returns True if the items are equal, else False.
    """

    return function[0] == function[1]


def if_(template: Dict, function: list) -> Any:
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


def ref(template: "Template", vaname: str) -> Union[str, int, float, list]:
    """Takes the name of a parameter, resource or pseudo variable and finds the value for it.

    Args:
        template (Dict): The Cloudformation template.
        vaname (str): The name of the parameter, resource or pseudo variable.

    Raises:
        ValueError: If the supplied pseudo variable doesn't exist.

    Returns:
        Union[str, int, float, list]: The value of the parameter, resource or pseudo variable.
    """

    if "AWS::" in vaname:
        pseudo = vaname.replace("AWS::", "")

        # Can't treat region like a normal pseduo because
        # we don't want to update the class var for every run.
        if pseudo == "Region":
            return template.template["Metadata"]["Cloud-Radar"]["Region"]
        try:
            return getattr(template, pseudo)
        except AttributeError:
            raise ValueError(f"Unrecognized AWS Pseduo variable: '{vaname}'.")

    if vaname in template.template["Parameters"]:
        return template.template["Parameters"][vaname]["Value"]
    else:
        return vaname


def sub(template: "Template", function: str) -> str:
    """Solves AWS Sub intrinsic functions.

    Args:
        function (str): A string with ${} parameters or resources referenced in the template.

    Returns:
        str: Returns the rendered string.
    """  # noqa: B950

    def replace_var(m):
        var = m.group(2)
        return ref(template, var)

    reVar = r"(?!\$\{\!)\$(\w+|\{([^}]*)\})"

    if re.search(reVar, function):
        return re.sub(reVar, replace_var, function).replace("${!", "${")

    return function.replace("${!", "${")
