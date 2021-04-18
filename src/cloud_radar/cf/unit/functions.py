"""AWS Intrinsic functions.

This module contains the logic to solve both AWS Intrinsic
and Condition functions.
"""

import base64 as b64
import ipaddress
import json
import re
from typing import Any, List, TYPE_CHECKING, Union

import requests

REGION_DATA = None

if TYPE_CHECKING:
    from ._template import Template


def base64(_t: "Template", value: Any) -> str:

    if not isinstance(value, str):
        raise Exception(
            f"The value for !Base64 or Fn::Base64 must be a String, not {type(value).__name__}."
        )

    b_string = b64.b64encode(value.encode("ascii"))

    return b_string.decode("ascii")


def cidr(_t: "Template", value: Any) -> List[str]:

    if not isinstance(value, list):
        raise Exception(
            f"The value for !Cidr or Fn::Cidr must be a List, not {type(value).__name__}."
        )

    if not len(value) == 3:
        raise Exception(
            (
                "The value for !Cidr or Fn::Cidr must contain "
                "a ipBlock, the count of subnets and the cidrBits."
            )
        )

    ip_block: str = value[0]
    count = int(value[1])
    hostBits = int(value[2])

    mask = 32 - hostBits

    network = ipaddress.IPv4Network(ip_block, strict=True)

    subnets = network.subnets(new_prefix=mask)

    try:
        return [next(subnets).exploded for _ in range(count)]
    except Exception:
        raise Exception(
            f"!Cidr or Fn::Cidr unable to convert {ip_block} into {count} subnets of /{mask}"
        )


def and_(_t: "Template", equation: Any) -> bool:
    raise NotImplementedError("Fn::And had not been implemented.")


def equals(_t: "Template", equation: Any) -> bool:
    """Solves AWS Equals intrinsic function.

    Args:
        _t (Template): Not used
        equation (Any): The equation to be solved.

    Raises:
        TypeError: If equation is not a list.
        ValueError: If length of equation is not 2.

    Returns:
        bool: True if the values in the equation are equal.
    """

    if not isinstance(equation, list):
        raise TypeError(
            f"Fn::Equals - The equations must be a List, not {type(equation).__name__}."
        )

    if not len(equation) == 2:
        raise ValueError(
            (
                "The equation for !Equals or Fn::Equals must contain "
                "two values to compare."
            )
        )

    return equation[0] == equation[1]


def if_(template: "Template", equation: Any) -> Any:
    """Solves AWS If intrinsic functions.

    Args:
        template (Template): The template being tested.
        equation (Any): The equation to be solved.

    Raises:
        TypeError: If equation is not a list.
        ValueError: If length of equation is not 3.
        TypeError: If the first value in the equation is not str.

    Returns:
        Any: The result of the equation.
    """

    if not isinstance(equation, list):
        raise TypeError(
            f"The equation for !If or Fn::If must be a List, not {type(equation).__name__}."
        )

    if not len(equation) == 3:
        raise ValueError(
            (
                "The equation for !If or Fn::If must contain "
                "the name of a condition, a True value and "
                "a False value."
            )
        )

    condition = equation[0]

    if not isinstance(condition, str):
        raise TypeError(f"AWS Condition should be str, not {type(condition).__name__}.")

    condition = template.template["Conditions"][condition]

    if condition:
        return equation[1]

    return equation[2]


def not_(_t: "Template", equation: Any) -> bool:
    raise NotImplementedError("Fn::Not had not been implemented.")


def or_(_t: "Template", equation: Any) -> bool:
    raise NotImplementedError("Fn::Or had not been implemented.")


def find_in_map(template: "Template", equation: Any) -> Any:
    """Solves AWS FindInMap intrinsic function.

    Args:
        template (Template): The template being tested.
        equation (Any): The equation to be solved.

    Raises:
        TypeError: If equation is not a list.
        ValueError: If length of equation is not 3.
        KeyError: If the Map or specified keys are missing.

    Returns:
        Any: The requested value from the Map.
    """

    if not isinstance(equation, list):
        raise TypeError(
            f"Fn::FindInMap - The equation must be a List, not {type(equation).__name__}."
        )

    if not len(equation) == 3:
        raise ValueError(
            (
                "The equation for !FindInMap  or Fn::FindInMap  must contain "
                "a MapName, TopLevelKey and SecondLevelKey."
            )
        )

    map_name = equation[0]
    top_key = equation[1]
    second_key = equation[2]

    if "Mappings" not in template.template:
        raise KeyError("Unable to find Mappings section in template.")

    maps = template.template["Mappings"]

    if map_name not in maps:
        raise KeyError(f"Unable to find {map_name} in Mappings section of template.")

    map = maps[map_name]

    if top_key not in map:
        raise KeyError(f"Unable to find key {top_key} in map {map_name}.")

    first_level = map[top_key]

    if second_key not in first_level:
        raise KeyError(f"Unable to find key {second_key} in map {map_name}.")

    return first_level[second_key]


def get_att(template: "Template", equation: Any) -> str:
    """Solves AWS GetAtt intrinsic function.

    Args:
        template (Template): The template being tested.
        equation (Any): The equation to be solved.

    Raises:
        TypeError: If equation is not a list.
        ValueError: If length of equation is not 3.
        TypeError: If the logicalNameOfResource and attributeName are not str.
        KeyError: If the logicalNameOfResource is not found in the template.

    Returns:
        str: The interpolated str `logicalNameOfResource.attributeName`.
    """

    if not isinstance(equation, list):
        raise TypeError(
            f"Fn::GetAtt - The equation must be a List, not {type(equation).__name__}."
        )

    if not len(equation) == 2:
        raise ValueError(
            (
                "Fn::GetAtt - The equation must contain "
                "the logicalNameOfResource and attributeName."
            )
        )

    resource_name = equation[0]
    att_name = equation[1]

    if not isinstance(resource_name, str) or not isinstance(att_name, str):
        raise TypeError(
            "Fn::GetAtt - logicalNameOfResource and attributeName must be String."
        )

    if resource_name not in template.template["Resources"]:
        raise KeyError(f"Fn::GetAtt - Resource {resource_name} not found in template.")

    return f"{resource_name}.{att_name}"


def get_azs(_t: "Template", region: Any) -> List[str]:
    """Solves AWS GetAZs intrinsic function.

    Args:
        _t (Template): The template being tested.
        region (Any): The name of a region.

    Raises:
        TypeError: If region is not a string.

    Returns:
        List[str]: The list of AZs for the provided region.
    """

    if not isinstance(region, str):
        raise TypeError(
            f"Fn::GetAZs - The region must be a String, not {type(region).__name__}."
        )

    return get_region_azs(region)


def import_value(template: "Template", name: Any) -> str:
    """Solves AWS ImportValue intrinsic function.

    Args:
        template (Template): The template being tested.
        name (Any): The name of the Export to be Imported.

    Raises:
        TypeError: If name is not a String.
        ValueError: If no imports have been configured.
        KeyError: If name is not found in the imports.

    Returns:
        str: The value of name from the configured imports.
    """

    if not isinstance(name, str):
        raise TypeError(
            "Fn::ImportValue - The name of the Export "
            f"should be String, not {type(name).__name__}."
        )

    if not template.imports:
        raise ValueError("Fn::ImportValue - No imports have been configued.")

    if name not in template.imports:
        raise KeyError(f"Fn::ImportValue - {name} not found in the configured imports.")

    return template.imports[name]


def join(_t: "Template", value: Any) -> str:

    delimiter: str
    items: List[str]

    if not isinstance(value, list):
        raise Exception(
            f"The value for !Join or Fn::Join must be list not {type(value).__name__}."
        )

    if not len(value) == 2:
        raise Exception(
            (
                "The value for !Join or Fn::Join must contain "
                "a delimiter and a list of items to join."
            )
        )

    if isinstance(value[0], str) and isinstance(value[1], list):
        delimiter = value[0]
        items = value[1]
    else:
        raise Exception(
            "The first value for !Join or Fn::Join must be a String and the second a List."
        )

    return delimiter.join(items)


def select(_t: "Template", equation: Any) -> Any:
    raise NotImplementedError("Fn::Select has not been implemented.")


def split(_t: "Template", equation: Any) -> List[str]:
    raise NotImplementedError("Fn::Split had not been implemented.")


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


def transform(template: "Template", equation: Any) -> Any:
    raise NotImplementedError("Fn::Transform has not been implemented.")


def ref(template: "Template", var_name: str) -> Union[str, int, float, list]:
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
            return template.template["Metadata"]["Cloud-Radar"]["Region"]
        try:
            return getattr(template, pseudo)
        except AttributeError:
            raise ValueError(f"Unrecognized AWS Pseduo variable: '{var_name}'.")

    if var_name in template.template["Parameters"]:
        return template.template["Parameters"][var_name]["Value"]
    else:
        return var_name


def get_region_azs(region_name: str) -> List[str]:

    global REGION_DATA

    if not REGION_DATA:
        REGION_DATA = _fetch_region_data()

    for region in REGION_DATA:
        if region["code"] == region_name:
            return region["zones"]

    raise Exception(f"Unable to find region {region_name}.")


def _fetch_region_data() -> List[dict]:

    url = "https://raw.githubusercontent.com/jsonmaur/aws-regions/master/regions.json"

    r = requests.get(url)

    if not r.status_code == requests.codes.ok:
        r.raise_for_status()

    return json.loads(r.text)
