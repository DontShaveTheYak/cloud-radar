from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

import yaml  # noqa: I100
from cfn_tools import dump_yaml, load_yaml  # type: ignore  # noqa: I100, I201

from . import functions
from ._hooks import HookProcessor
from ._stack import Stack

IntrinsicFunc = Callable[["Template", Any], Any]


class Template:
    """Loads a Cloudformation template file so that it's parameters
    and conditions can be rendered into their final form for testing.
    """

    AccountId: str = "5" * 12
    Hooks = HookProcessor()
    NotificationARNs: list = []
    NoValue: str = ""  # Not yet implemented
    Partition: str = "aws"  # Other regions not implemented
    Region: str = "us-east-1"
    StackId: str = ""  # If left blank this will be generated
    StackName: str = "my-cloud-radar-stack"
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
        self.transforms: Optional[Union[str, List[str]]] = self.template.get(
            "Transform", None
        )
        self.allowed_functions: functions.Dispatch = self.load_allowed_functions()

        # All loaded, validate against any template level hooks
        # that have been configured
        self.Hooks.evaluate_template_hooks(self)

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
        self,
        params: Optional[Dict[str, str]] = None,
        region: Optional[str] = None,
        parameters_file: Optional[str] = None,
    ) -> dict:
        """Solves all conditionals, references and pseudo variables using
        the passed in parameters. After rendering the template all resources
        that wouldn't get deployed because of a condition statement are removed.

        Args:
            params (dict, optional): Parameter names and values to be used when rendering.
            region (str, optional): The region is used for the AWS::Region pseudo variable. Defaults to "us-east-1".
            parameters_file (str, optional): Path to a parameters file to load. If this is supplied as well as params,
                                    anything in params will take precedence.

        Returns:
            dict: The rendered template.
        """  # noqa: B950

        if region:
            self.Region = region

        if parameters_file:
            # Attempt to load params from a file.
            loaded_params = self.load_params(parameters_file)
            # If a file and a parameter dict were supplied,
            # the parameter dict will take precedence.
            if params:
                loaded_params.update(params)

            params = loaded_params

        self.template = yaml.load(self.raw, Loader=yaml.FullLoader)
        self.set_parameters(params)

        add_metadata(self.template, self.Region)

        self.template = self.render_all_sections(self.template)

        self.template = self.remove_condtional_resources(self.template)

        return self.template

    def load_params(self, parameter_file_path) -> Dict[str, Any]:
        # There are ??? main formats for configuration files which are used by
        # different AWS tools.
        # All of these are JSON based, but are formatted differently internally.
        # We want to look for hints and get out a common format.

        with parameter_file_path.open() as f:
            json_content = json.load(f)

            if "Parameters" in json_content:
                # This is a CodePipeline CloudFormation artifact format file
                # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/continuous-delivery-codepipeline-cfn-artifacts.html#w4ab1c21c15c15
                return json_content["Parameters"]

            if isinstance(json_content, list) and "ParameterKey" in json_content[0]:
                # This file looks like the type of parameters that the CloudFormation
                # CLI supports
                # https://awscli.amazonaws.com/v2/documentation/api/latest/reference/cloudformation/create-stack.html

                # Takes something in the format:
                #     [
                #         {
                #             "ParameterKey": "Key1",
                #             "ParameterValue": "Value1"
                #         },
                #         {
                #             "ParameterKey": "Key2",
                #             "ParameterValue": "Value2"
                #         }
                #     ]
                #
                #     And turns it in to:
                #     {
                #         "Key1": "Value1",
                #         "Key2": "Value2
                #     }
                params = {}
                for param in json_content:
                    params[param["ParameterKey"]] = param["ParameterValue"]

                return params

            # If we get this far then we do not support this type of configuration file
            raise ValueError("Parameter file is not in a supported format")

    def load_allowed_functions(self):
        """Loads the allowed functions for this template.

        Raises:
            ValueError: If the transform is not supported.
            ValueError: If the Transform section is not a string or list.

        Returns:
            functions.Dispatch: A dictionary of allowed functions.
        """
        if self.transforms is None:
            return functions.ALL_FUNCTIONS

        if isinstance(self.transforms, str):
            if self.transforms not in functions.TRANSFORMS:
                raise ValueError(f"Transform {self.transforms} not supported")

            # dict of transform functions
            transform_functions = functions.TRANSFORMS[self.transforms]

            # return the merger of ALL_FUNCTIONS and the transform functions
            return {**functions.ALL_FUNCTIONS, **transform_functions}

        if isinstance(self.transforms, list):
            transform_functions = {}

            for transform in self.transforms:
                if transform not in functions.TRANSFORMS:
                    raise ValueError(f"Transform {transform} not supported")
                transform_functions = {
                    **transform_functions,
                    **functions.TRANSFORMS[transform],
                }

            # return the merger of ALL_FUNCTIONS and the transform functions
            return {**functions.ALL_FUNCTIONS, **transform_functions}

        raise ValueError(f"Transform {self.transforms} not supported")

    def render_all_sections(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Solves all conditionals, references and pseudo variables for all sections"""

        if "Conditions" in template:
            template["Conditions"] = self.resolve_values(template["Conditions"])

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

                template[section][r_name] = self.resolve_values(r_value)

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

    # If the StackId variable is not set, generate a value for it
    def _get_populated_stack_id(self) -> str:
        if not Template.StackId:
            # Not explicitly set, generate a value
            unique_uuid = uuid.uuid4()

            return (
                f"arn:{Template.Partition}:cloudformation:{self.Region}:"
                f"{Template.AccountId}:stack/{Template.StackName}/{unique_uuid}"
            )

        return Template.StackId

    def create_stack(
        self,
        params: Optional[Dict[str, str]] = None,
        region: Optional[str] = None,
        parameters_file: Optional[str] = None,
    ):
        if region:
            self.Region = region
        self.StackId = self._get_populated_stack_id()

        self.render(params, parameters_file=parameters_file)

        stack = Stack(self.template)

        # Evaluate any hooks prior to returning this stack
        self.Hooks.evaluate_resource_hooks(stack, self)

        return stack

    def resolve_values(  # noqa: max-complexity: 13
        self,
        data: Any,
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
                    data[key] = self.resolve_values(value)
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
                    data[key] = self.resolve_values(value)
                    continue

                if key not in self.allowed_functions:
                    raise ValueError(f"{key} with value ({value}) not allowed here")

                value = self.resolve_values(value)

                funct_result = self.allowed_functions[key](self, value)

                if isinstance(funct_result, str):
                    # If the result is a string then process any
                    # dynamic references first
                    return self.resolve_dynamic_references(funct_result)

                return funct_result

            return data
        elif isinstance(data, list):
            return [self.resolve_values(item) for item in data]
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

        dynamic_reference_value = self._get_dynamic_reference_value(service, key)

        updated_value = data.replace(
            f"{{{{resolve:{service}:{key}}}}}",
            dynamic_reference_value,
        )

        # run the updated value through this function again
        # to pick up any other references
        return self.resolve_dynamic_references(updated_value)

    def _get_dynamic_reference_value(self, service: str, key: str) -> str:
        """
        Gets a value from the dynamic references map.

        This will raise errors if the specified service / key is not in the map.

        Args:
            service (str): the service the reference is for
            key (str): the parameter key

        Raises:
            KeyError: if the service does not exist in the dynamic references map
            KeyError: if the key does not exist in the dynamic references map for the service
        """

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

        return self.dynamic_references[service][key]

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

        params_not_in_template = set(parameters) - set(t_params)
        if params_not_in_template:
            raise ValueError(
                (
                    "You supplied one or more Parameters that were not in the "
                    f"Template - {params_not_in_template}"
                )
            )

        for p_name, p_value in t_params.items():
            if p_name in parameters:
                validate_parameter_constraints(
                    p_name, t_params[p_name], parameters[p_name]
                )

                t_params[p_name]["Value"] = parameters[p_name]
                continue

            if "Default" not in p_value:
                raise ValueError(
                    (
                        f'Must provide values for parameter "{p_name}" '
                        "that does not have a default value."
                    )
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
        updated_definition = parameter_definition.copy()
        updated_definition["Type"] = trimmed_type

        for part in parameter_value.split(","):
            validate_parameter_constraints(
                parameter_name, updated_definition, part.strip()
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

    # There are a few variants of SSM parameters, but they all have the
    # same regex pattern
    #
    # This is based on the documentation for the PutParameter API operation
    # https://docs.aws.amazon.com/systems-manager/latest/APIReference/
    # API_PutParameter.html#systemsmanager-PutParameter-request-Name
    #
    ssm_parameter_value_regex = r"^([/]{0,1}[a-zA-Z0-9_.-]*){1,15}$"

    if parameter_type.startswith("AWS::SSM::Parameter::Value<"):
        # SSM parameter, need to validate that the type in the angle brackets
        # is a supported one

        supported_ssm_value_types = [
            "String",
            "List<String>",
            "CommaDelimitedList",
            "AWS::EC2::AvailabilityZone::Name",
            "AWS::EC2::Image::Id",
            "AWS::EC2::Instance::Id",
            "AWS::EC2::SecurityGroup::Id",
            "AWS::EC2::Subnet::Id",
            "AWS::EC2::VPC::Id",
            "AWS::EC2::Volume::Id",
            "AWS::EC2::SecurityGroup::GroupName",
            "AWS::Route53::HostedZone::Id"
            "AWS::EC2::KeyPair::KeyName"
            "List<AWS::EC2::AvailabilityZone::Name>",
            "List<AWS::EC2::Image::Id>",
            "List<AWS::EC2::Instance::Id>",
            "List<AWS::EC2::SecurityGroup::Id>",
            "List<AWS::EC2::Subnet::Id>",
            "List<AWS::EC2::VPC::Id>",
            "List<AWS::EC2::Volume::Id>",
            "List<AWS::EC2::SecurityGroup::GroupName>",
            "List<AWS::Route53::HostedZone::Id>" "List<AWS::EC2::KeyPair::KeyName>",
        ]

        value_type = parameter_type[27:-1]
        if value_type not in supported_ssm_value_types:
            raise ValueError(
                (
                    f"Type {value_type} is not a supported SSM value type for "
                    f" SSM parameter {parameter_name}"
                )
            )

        if not re.match(ssm_parameter_value_regex, parameter_value):
            raise ValueError(
                (
                    f"Value {parameter_value} does not match the expected pattern "
                    f"for SSM parameter {parameter_name}."
                )
            )

    else:
        # Other AWS parameter types

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
            # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-security-group.html#cfn-ec2-securitygroup-groupname # noqa B950
            "AWS::EC2::SecurityGroup::GroupName": r"^[a-zA-Z0-9 ._\-:\/()#,@\[\]+=&;{}!$*]{1,255}$",  # noqa B950
            # Bit of a guess this one, not sure what the minimum bound should be
            # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-route53-recordset.html#cfn-route53-recordset-hostedzoneid # noqa B950
            "AWS::Route53::HostedZone::Id": "^[A-Z0-9]{,32}$",
            # All the docs say for this type is up to 255 ascii characters
            "AWS::EC2::KeyPair::KeyName": "^[ -~]{1,255}$",
            "AWS::SSM::Parameter::Name": ssm_parameter_value_regex,
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
    as metadata because we can't treat Region like a normal pseudo
    variables because we don't want to update the class var for every run.

    Args:
        template (Dict): The template you want to update.
        region (str): The region that template will be tested with.
    """

    if "Metadata" not in template:
        template["Metadata"] = {}

    # Get the existing metadata (so we do not overwrite any
    # hook suppressions), then set the region into it before
    # updating the template
    cloud_radar_metadata = template["Metadata"].get("Cloud-Radar", {})
    cloud_radar_metadata["Region"] = region

    template["Metadata"]["Cloud-Radar"] = cloud_radar_metadata


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
