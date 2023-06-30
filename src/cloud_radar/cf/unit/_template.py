from __future__ import annotations

import re
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
        self,
        template: Dict[str, Any],
        imports: Optional[Dict[str, str]] = None,
        dynamic_references: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> None:
        """Loads a Cloudformation template from a file and saves
        it as a dictionary.

        Args:
            template (Dict): The Cloudformation template as a dictionary.
            imports (Optional[Dict[str, str]], optional): Values this template plans
            to import from other stacks exports. Defaults to None.
            dynamic_references (Optional[Dict[str, Dict[str, str]]], optional): Values
            this template plans to dynamically lookup from ssm/secrets manager.
            Defaults to None.

        Raises:
            TypeError: If template is not a dictionary.
            TypeError: If imports is not a dictionary.
            TypeError: If dynamic_references is not a dictionary.
        """

        if imports is None:
            imports = {}

        if dynamic_references is None:
            dynamic_references = {}

        if not isinstance(template, dict):
            raise TypeError(
                f"Template should be a dict, not {type(template).__name__}."
            )

        if not isinstance(imports, dict):
            raise TypeError(f"Imports should be a dict, not {type(imports).__name__}.")

        if not isinstance(dynamic_references, dict):
            raise TypeError(
                f"Dynamic References should be a dict, not {type(dynamic_references).__name__}."
            )

        self.raw: str = yaml.dump(template)
        self.template = template
        self.Region = Template.Region
        self.imports = imports
        self.dynamic_references = dynamic_references

    @classmethod
    def from_yaml(
        cls,
        template_path: Union[str, Path],
        imports: Optional[Dict[str, str]] = None,
        dynamic_references: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Template:
        """Loads a Cloudformation template from file.

        Args:
            template_path (Union[str, Path]): The path to the template.
            imports (Optional[Dict[str, str]], optional): Values this template plans
            to import from other stacks exports. Defaults to None.
            dynamic_references (Optional[Dict[str, Dict[str, str]]], optional): Values
            this template plans to dynamically lookup from ssm/secrets manager.
            Defaults to None.

        Returns:
            Template: A Template object ready for testing.
        """

        with open(template_path) as f:
            raw = f.read()

        tmp_yaml = load_yaml(raw)

        tmp_str = dump_yaml(tmp_yaml)

        template = yaml.load(tmp_str, Loader=yaml.FullLoader)

        return cls(template, imports, dynamic_references)

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
                if section == "Resources" and "Properties" not in r_value:
                    # While the Properties key is technically optional,
                    # our processing requires it to be there to distinguish
                    # this as a Resource when we perform further rendering
                    r_value["Properties"] = {}

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

    def resolve_values(  # noqa: max-complexity: 13
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

                funct_result = allowed_func[key](self, value)

                if isinstance(funct_result, str):
                    # If the result is a string then process any
                    # dynamic references first
                    return self.resolve_dynamic_references(funct_result)

                return funct_result

            return data
        elif isinstance(data, list):
            return [
                self.resolve_values(
                    item,
                    allowed_func,
                )
                for item in data
            ]
        elif isinstance(data, str):
            return self.resolve_dynamic_references(data)
        else:
            return data

    def resolve_dynamic_references(self, data: str) -> str:
        """
        Replaces any dynamic references in the provided data with values from
        our configuration.

        Args:
            data (str): the value to replace dynamic references within

        Raises:
            ValueError: If a dynamic reference has been used and no dynamic
            references have been configured.
            KeyError: If a dynamic reference name has been used and is not
            found in the configuration
        """

        if "${" in data:
            # If the value contains a "${" then it is likely we are meant to
            # apply other functions to it before processing the result (like
            # a Fn::Sub first to include an AWS account ID)
            return data

        if "{{resolve:" not in data:
            # This is not a dynamic reference so just return the string
            return data

        matches = re.search(
            r"{{resolve:([^:]+):(.*?)}}",
            data,
        )

        if not matches:
            raise ValueError(
                f"Found '{{{{resolve' in string, but did not match expected regex - {data}"
            )

        service = matches.group(1)
        key = matches.group(2)

        if service not in self.dynamic_references:
            raise KeyError(
                f"Service {service} not included in dynamic references configuration"
            )
        if key not in self.dynamic_references[service]:
            raise KeyError(
                (
                    f"Key {key} not included in dynamic references "
                    f"configuration for service {service}"
                )
            )

        updated_value = data.replace(
            f"{{{{resolve:{service}:{key}}}}}",
            self.dynamic_references[service][key],
        )

        # run the updated value through this function again
        # to pick up any other references
        return self.resolve_dynamic_references(updated_value)

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
                validate_parameter_constraints(
                    p_name, t_params[p_name], parameters[p_name]
                )

                t_params[p_name]["Value"] = parameters[p_name]
                continue

            if "Default" not in p_value:
                raise ValueError(
                    "Must provide values for parameters that don't have a default value."
                )

            t_params[p_name]["Value"] = p_value["Default"]


def validate_parameter_constraints(
    parameter_name: str, parameter_definition: dict, parameter_value: str
):
    """
    Validate that the parameter value matches any constraints
    for allowed values, allowed patterns etc.
    This method will raise a ValueError if any validation constraints
    are not met.
    Args:
        parameter_name (str): The name of the parameter being validated
        parameter_definition (Dict): The parameter definition being validated
                                    against
        parameter_value (str): The supplied parameter value being validated
    """

    if parameter_definition["Type"] == "String":
        validate_string_parameter_constraints(
            parameter_name, parameter_definition, parameter_value
        )
    elif parameter_definition["Type"] == "CommaDelimitedList":
        # When applied to a parameter of type CommaDelimitedList,
        # each value in the list must meet the String type criteria
        for part in parameter_value.split(","):
            validate_string_parameter_constraints(
                parameter_name, parameter_definition, part.strip()
            )
    elif parameter_definition["Type"] == "Number":
        validate_number_parameter_constraints(
            parameter_name, parameter_definition, parameter_value
        )
    elif parameter_definition["Type"].startswith("AWS::"):
        validate_aws_parameter_constraints(
            parameter_name, parameter_definition["Type"], parameter_value
        )
    elif parameter_definition["Type"].startswith("List<"):
        # All list types runs the single value validation for all items
        trimmed_type = parameter_definition["Type"][5:-1]

        # There are a couple though that are not supported
        if trimmed_type == "AWS::EC2::KeyPair::KeyName" or trimmed_type == "String":
            # this is a type that isn't valid as a list, but is
            # as a single item
            raise ValueError(f"Type {trimmed_type} is not valid in a List<>")

        # Iterate over each item and call this method again with an
        # updated definition for the non-list type
        updated_defintion = parameter_definition.copy()
        updated_defintion["Type"] = trimmed_type

        for part in parameter_value.split(","):
            validate_parameter_constraints(
                parameter_name, updated_defintion, part.strip()
            )


def validate_aws_parameter_constraints(
    parameter_name: str, parameter_type: str, parameter_value: str
):
    """
    Validate that the parameter value matches any constraints
    that are applicable for an AWS type parameter

    This method will raise a ValueError if any validation constraints
    are not met.
    Args:
        parameter_name (str): The name of the parameter being validated
        parameter_type (str): The AWS type of the parameter being validated
                                    against
        parameter_value (str): The supplied parameter value being validated
    """

    parameter_type_regexes = {
        # Reference for this was
        # https://gist.github.com/rams3sh/4858d5150acba5383dd697fda54dda2c
        "AWS::EC2::AvailabilityZone::Name": (
            "^(af|ap|ca|eu|me|sa|us)-(central|north|(north(?:east|west))|"
            "south|south(?:east|west)|east|west)-[0-9]+[a-z]{1}$"
        ),
        # Reference for the next few are
        # https://blog.skeddly.com/2016/01/long-ec2-instance-ids-are-fully-supported.html
        "AWS::EC2::Image::Id": "^ami-[a-f0-9]{8}([a-f0-9]{9})?$",
        "AWS::EC2::Instance::Id": "^i-[a-f0-9]{8}([a-f0-9]{9})?$",
        "AWS::EC2::SecurityGroup::Id": "^sg-[a-f0-9]{8}([a-f0-9]{9})?$",
        "AWS::EC2::Subnet::Id": "^subnet-[a-f0-9]{8}([a-f0-9]{9})?$",
        "AWS::EC2::VPC::Id": "^vpc-[a-f0-9]{8}([a-f0-9]{9})?$",
        "AWS::EC2::Volume::Id": "^vol-[a-f0-9]{8}([a-f0-9]{9})?$",
        # Reference for this was
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-security-group.html#cfn-ec2-securitygroup-groupname
        "AWS::EC2::SecurityGroup::GroupName": r"^[a-zA-Z0-9 ._\-:\/()#,@\[\]+=&;{}!$*]{1,255}$",
        # Bit of a guess this one, not sure what the minimum bound should be
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-route53-recordset.html#cfn-route53-recordset-hostedzoneid
        "AWS::Route53::HostedZone::Id": "^[A-Z0-9]{,32}$",
        # All the docs say for this type is up to 255 ascii characters
        "AWS::EC2::KeyPair::KeyName": "^[ -~]{1,255}$",
    }
    param_regex = parameter_type_regexes.get(parameter_type)

    if param_regex is None:
        # If a regex is defined, we know the regex to validate the parameter
        raise KeyError(f"Unsupported parameter type {parameter_type}")

    if not re.match(param_regex, parameter_value):
        raise ValueError(
            (
                f"Value {parameter_value} does not match the expected pattern "
                f"for parameter {parameter_name} and type {parameter_type}"
            )
        )


def validate_number_parameter_constraints(
    parameter_name: str, parameter_definition: dict, parameter_value: str
):
    """
    Validate that the parameter value matches any constraints
    that are applicable for Number value parameters
    (min/max value)
    This method will raise a ValueError if any validation constraints
    are not met.
    Args:
        parameter_name (str): The name of the parameter being validated
        parameter_definition (Dict): The parameter definition being validated
                                    against
        parameter_value (str): The supplied parameter value being validated
    """
    if "MinValue" in parameter_definition and int(parameter_value) < int(
        parameter_definition["MinValue"]
    ):
        raise ValueError(
            (
                f"Value {parameter_value} is below the minimum value for"
                f" parameter {parameter_name}"
            )
        )

    if "MaxValue" in parameter_definition and int(parameter_value) > int(
        parameter_definition["MaxValue"]
    ):
        raise ValueError(
            (
                f"Value {parameter_value} is above the maximum value for"
                f" parameter {parameter_name}"
            )
        )


def validate_string_parameter_constraints(
    parameter_name: str, parameter_definition: dict, parameter_value: str
):
    """
    Validate that the parameter value matches any constraints
    that are applicable for String value parameters
    (allowed values, allowed patterns, min/max length)
    This method will raise a ValueError if any validation constraints
    are not met.
    Args:
        parameter_name (str): The name of the parameter being validated
        parameter_definition (Dict): The parameter definition being validated
                                    against
        parameter_value (str): The supplied parameter value being validated
    """

    # Compare allowed values
    if (
        "AllowedValues" in parameter_definition
        and parameter_value not in parameter_definition["AllowedValues"]
    ):
        raise ValueError(
            (
                f"Value {parameter_value} not in allowed "
                f"values for parameter {parameter_name}"
            )
        )

    if "AllowedPattern" in parameter_definition and not re.match(
        parameter_definition["AllowedPattern"], parameter_value
    ):
        raise ValueError(
            (
                f"Value {parameter_value} does not match the AllowedPattern "
                f"for parameter {parameter_name}"
            )
        )

    if "MinLength" in parameter_definition and len(parameter_value) < int(
        parameter_definition["MinLength"]
    ):
        raise ValueError(
            (
                f"Value {parameter_value} is shorter than the minimum length for"
                f" parameter {parameter_name}"
            )
        )

    if "MaxLength" in parameter_definition and len(parameter_value) > int(
        parameter_definition["MaxLength"]
    ):
        raise ValueError(
            (
                f"Value {parameter_value} is longer than the maximum length for"
                f" parameter {parameter_name}"
            )
        )


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
