"""
AWS Fn::ForEach intrinsic implementation.


This implementation (and the matching piece in
_template.py), was based on the AWS documentation
including the Fn::ForEach RFC and examples pages.
"""

# https://github.com/aws-cloudformation/cfn-language-discussion/blob/main/RFCs/0009-Fn%3A%3AForEach.md  # noqa: E501
# https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/intrinsic-function-reference-foreach-examples.html  # noqa: E501

import copy
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

if TYPE_CHECKING:
    from ._template import Template

Replacement = Tuple[str, Any, str]


def _validate_for_each_inputs(values: Any) -> tuple[str, Any, dict]:
    """Validate inputs for Fn::ForEach and extract the loop components.

    Args:
        values (Any): The values passed to the function.

    Raises:
        TypeError: If values is not a list or components have wrong types.
        ValueError: If length of values is not 3.

    Returns:
        tuple[str, Any, dict]: The identifier, collection, and output template.
    """

    if not isinstance(values, list):
        raise TypeError(
            f"Fn::ForEach - The values must be a List, not {type(values).__name__}."
        )

    if len(values) != 3:
        raise ValueError(
            (
                "Fn::ForEach - The values must contain an identifier, a collection, "
                "and an output template."
            )
        )

    identifier = values[0]
    collection = values[1]
    output_template = values[2]

    if not isinstance(identifier, str):
        raise TypeError(
            f"Fn::ForEach - The identifier must be a String, not {type(identifier).__name__}."
        )

    if not isinstance(collection, (list, dict)):
        raise TypeError(
            (
                "Fn::ForEach - The collection must be a List or Dict, "
                f"not {type(collection).__name__}."
            )
        )

    if not isinstance(output_template, dict):
        raise TypeError(
            (
                "Fn::ForEach - The output template must be a Dict, not "
                f"{type(output_template).__name__}."
            )
        )

    return identifier, collection, output_template


def _apply_string_replacement(value: str, replacement: Replacement) -> str:
    """Apply a single Fn::ForEach replacement to a string value.

    Args:
        value (str): The string to update.
        replacement (Replacement): The loop replacement tuple.

    Returns:
        str: The updated string.
    """

    identifier, replacement_value, alphanumeric_replacement = replacement

    result = value.replace(f"${{{identifier}}}", str(replacement_value))
    return result.replace(f"&{{{identifier}}}", alphanumeric_replacement)


def _substitute_ref(
    obj: dict, replacement: Replacement, remaining_replacements: list[Replacement]
) -> Optional[Any]:
    """Substitute a Ref that points at the current loop identifier.

    Args:
        obj (dict): The object being processed.
        replacement (Replacement): The current loop replacement tuple.
        remaining_replacements (list[Replacement]): Remaining replacements to apply.

    Returns:
        Optional[Any]: The substituted value, or None if this is not a matching Ref.
    """

    identifier, replacement_value, _ = replacement

    if len(obj) == 1 and "Ref" in obj and obj["Ref"] == identifier:
        return _substitute_for_each(replacement_value, remaining_replacements)

    return None


def _substitute_sub(
    obj: dict, replacement: Replacement, remaining_replacements: list[Replacement]
) -> Optional[Any]:
    """Substitute loop variables inside Fn::Sub values.

    Args:
        obj (dict): The object being processed.
        replacement (Replacement): The current loop replacement tuple.
        remaining_replacements (list[Replacement]): Remaining replacements to apply.

    Returns:
        Optional[Any]: The substituted value, or None if this is not an Fn::Sub.
    """

    if len(obj) != 1 or "Fn::Sub" not in obj:
        return None

    sub_value = obj["Fn::Sub"]
    if isinstance(sub_value, str):
        sub_result = _apply_string_replacement(sub_value, replacement)
        return _substitute_for_each({"Fn::Sub": sub_result}, remaining_replacements)

    if isinstance(sub_value, list) and len(sub_value) == 2:
        template_str, variables = sub_value
        if isinstance(template_str, str):
            template_str = _apply_string_replacement(template_str, replacement)
        if isinstance(variables, dict):
            variables = _substitute_for_each(variables, [replacement])
        return _substitute_for_each(
            {"Fn::Sub": [template_str, variables]}, remaining_replacements
        )

    return _substitute_for_each(obj, remaining_replacements)


def _substitute_get_att(
    obj: dict, replacement: Replacement, remaining_replacements: list[Replacement]
) -> Optional[Any]:
    """Substitute loop variables inside the list form of Fn::GetAtt.

    Args:
        obj (dict): The object being processed.
        replacement (Replacement): The current loop replacement tuple.
        remaining_replacements (list[Replacement]): Remaining replacements to apply.

    Returns:
        Optional[Any]: The substituted value, or None if this is not an Fn::GetAtt.
    """

    if len(obj) != 1 or "Fn::GetAtt" not in obj:
        return None

    identifier, replacement_value, _ = replacement
    get_att_value = obj["Fn::GetAtt"]

    if isinstance(get_att_value, list) and len(get_att_value) == 2:
        resource_name = _substitute_for_each(get_att_value[0], [replacement])
        attribute_name = get_att_value[1]

        if attribute_name == identifier:
            attribute_name = replacement_value
        else:
            attribute_name = _substitute_for_each(attribute_name, [replacement])

        return _substitute_for_each(
            {"Fn::GetAtt": [resource_name, attribute_name]}, remaining_replacements
        )

    return _substitute_for_each(obj, remaining_replacements)


def _substitute_nested_foreach(
    key: str,
    value: Any,
    replacement: Replacement,
) -> tuple[str, Any]:
    """Apply substitutions to a nested Fn::ForEach block without renaming its key.

    Args:
        key (str): The nested Fn::ForEach key.
        value (Any): The nested Fn::ForEach value.
        replacement (Replacement): The current loop replacement tuple.

    Returns:
        tuple[str, Any]: The preserved key and substituted value.
    """

    if isinstance(value, list) and len(value) == 3:
        return key, _substitute_for_each(value, [replacement])

    return key, value


def _substitute_regular_entry(
    key: str,
    value: Any,
    replacement: Replacement,
) -> tuple[Any, Any]:
    """Apply substitutions to a normal dictionary entry.

    Args:
        key (str): The dictionary key.
        value (Any): The dictionary value.
        replacement (Replacement): The current loop replacement tuple.

    Returns:
        tuple[Any, Any]: The substituted key and value.
    """

    new_key = _substitute_for_each(key, [replacement])
    new_value = _substitute_for_each(value, [replacement])
    return new_key, new_value


def _substitute_dict(
    obj: dict,
    replacement: Replacement,
    remaining_replacements: list[Replacement],
) -> Any:
    """Apply a single Fn::ForEach replacement to a dictionary.

    Args:
        obj (dict): The dictionary to update.
        replacement (Replacement): The current loop replacement tuple.
        remaining_replacements (list[Replacement]): Remaining replacements to apply.

    Returns:
        Any: The substituted dictionary or intrinsic result.
    """

    substituted_ref = _substitute_ref(obj, replacement, remaining_replacements)
    if substituted_ref is not None:
        return substituted_ref

    substituted_sub = _substitute_sub(obj, replacement, remaining_replacements)
    if substituted_sub is not None:
        return substituted_sub

    substituted_get_att = _substitute_get_att(obj, replacement, remaining_replacements)
    if substituted_get_att is not None:
        return substituted_get_att

    result_dict = {}
    for key, value in obj.items():
        if key.startswith("Fn::ForEach::"):
            new_key, new_value = _substitute_nested_foreach(key, value, replacement)
        else:
            new_key, new_value = _substitute_regular_entry(key, value, replacement)

        result_dict[new_key] = new_value

    return _substitute_for_each(result_dict, remaining_replacements)


def _substitute_for_each(obj: Any, replacements: list[Replacement]) -> Any:
    """Recursively apply Fn::ForEach substitutions to an object.

    Supports the standard ``${Identifier}`` placeholder and the alternative
    ``&{Identifier}`` placeholder that strips non-alphanumeric characters.

    Args:
        obj (Any): The object to substitute within.
        replacements (list[Replacement]): Ordered replacement tuples to apply.

    Returns:
        Any: The substituted object.
    """

    if not replacements:
        return obj

    replacement = replacements[0]
    remaining_replacements = replacements[1:]

    if isinstance(obj, str):
        result = _apply_string_replacement(obj, replacement)
        return _substitute_for_each(result, remaining_replacements)

    if isinstance(obj, dict):
        return _substitute_dict(obj, replacement, remaining_replacements)

    if isinstance(obj, list):
        result_list = [_substitute_for_each(item, [replacement]) for item in obj]
        return _substitute_for_each(result_list, remaining_replacements)

    return _substitute_for_each(obj, remaining_replacements)


def _get_alphanumeric_replacement(value: Any) -> str:
    """Build the alphanumeric-only replacement string for ``&{}`` placeholders.

    Args:
        value (Any): The current loop value.

    Returns:
        str: The loop value stripped of non-alphanumeric characters.
    """

    return re.sub(r"[^a-zA-Z0-9]", "", str(value))


def _process_for_each_item(
    identifier: str,
    item: Any,
    output_template: dict,
    post_process: Optional[Callable[[Any], Any]] = None,
) -> dict:
    """Build the expanded output for a single Fn::ForEach collection item.

    Args:
        identifier (str): The substitution identifier.
        item (Any): The current collection item.
        output_template (dict): The template to substitute into.
        post_process (Optional[Callable[[Any], Any]], optional): Optional callback
            for nested processing. Defaults to None.

    Returns:
        dict: The expanded dictionary for the current item.
    """

    replacement = (identifier, item, _get_alphanumeric_replacement(item))
    substituted = _substitute_for_each(output_template, [replacement])

    if post_process is not None:
        substituted = post_process(substituted)

    return substituted


def _process_for_each_collection(
    identifier: str,
    collection: Any,
    output_template: dict,
    post_process: Optional[Callable[[Any], Any]] = None,
) -> dict:
    """Process a collection and build the expanded Fn::ForEach result.

    Args:
        identifier (str): The substitution identifier.
        collection (Any): The collection to iterate over.
        output_template (dict): The template to substitute into.
        post_process (Optional[Callable[[Any], Any]], optional): Optional callback
            for nested processing. Defaults to None.

    Returns:
        dict: The expanded output dictionary.
    """

    result = {}
    items = collection if isinstance(collection, list) else collection.values()

    for item in items:
        result.update(
            _process_for_each_item(
                identifier,
                item,
                output_template,
                post_process=post_process,
            )
        )

    return result


def _resolve_collection(template: "Template", values: Any) -> Any:
    """Resolve the collection argument for Fn::ForEach before validation.

    Args:
        template (Template): The template being tested.
        values (Any): The original Fn::ForEach values.

    Returns:
        Any: The updated values with a resolved collection where possible.
    """

    if isinstance(values, list) and len(values) == 3:
        return [values[0], template.resolve_values(copy.deepcopy(values[1])), values[2]]

    return values


def for_each(
    template: "Template",
    values: Any,
    post_process: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, Any]:
    """Solve the AWS Fn::ForEach intrinsic function.

    Args:
        template (Template): The template being tested.
        values (Any): The values passed to the function.
        post_process (Optional[Callable[[Any], Any]], optional): Optional callback
            used to process nested Fn::ForEach output. Defaults to None.

    Returns:
        Dict[str, Any]: The expanded output dictionary.
    """

    resolved_values = _resolve_collection(template, values)
    identifier, collection, output_template = _validate_for_each_inputs(resolved_values)

    return _process_for_each_collection(
        identifier,
        collection,
        output_template,
        post_process=post_process,
    )


def _expand_foreach_entry(template: "Template", key: str, value: Any) -> dict:
    """Expand a single Fn::ForEach entry during template transformation.

    Args:
        template (Template): The template being tested.
        key (str): The Fn::ForEach key.
        value (Any): The Fn::ForEach value.

    Raises:
        ValueError: If the Fn::ForEach structure is invalid.

    Returns:
        dict: The expanded output for the ForEach entry.
    """

    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"Invalid Fn::ForEach structure for {key}")

    return for_each(
        template,
        value,
        post_process=lambda item: apply_foreach_transform(template, item),
    )


def apply_foreach_transform(template: "Template", data: Any) -> Any:
    """Recursively expand Fn::ForEach entries in a template structure.

    Args:
        template (Template): The template being tested.
        data (Any): The data structure to transform.

    Returns:
        Any: The transformed data structure.
    """

    if isinstance(data, dict):
        transformed = {}
        for key, value in data.items():
            if key.startswith("Fn::ForEach::"):
                transformed.update(_expand_foreach_entry(template, key, value))
            else:
                transformed[key] = apply_foreach_transform(template, value)
        return transformed

    if isinstance(data, list):
        return [apply_foreach_transform(template, item) for item in data]

    return data
