import re
from collections import UserDict
from typing import Any, Dict


class Resource(UserDict):
    def __init__(self, name: str, resource_data: Dict[str, Any]) -> None:
        super().__init__(resource_data)
        self.name = name

    # This check should be moved to inside the resolver?
    def has_type(self):
        """Check if the resource has a type."""
        assert "Type" in self.data, f"Resource '{self.name}' has no 'Type' attribute."

    def get_type_value(self) -> str:
        """Get the type of the resource.

        Returns:
            str: The type of the resource.
        """
        self.has_type()

        return self.data["Type"]

    def assert_type_is(self, type: str):
        """Assert that the type of the resource is equal to the given type.

        Args:
            type (str): The type to compare the resource type to.
        """
        actual_type = self.get_type_value()

        assert (
            type == actual_type
        ), f"Resource '{self.name}' type {actual_type} did not match input {type}"

    # We could have more condition checks but currently conditions are buggy
    # because we replace the name of the condition with the resolved value

    def has_properties(self):
        """Check if the resource has properties."""
        assert (
            "Properties" in self.data
        ), f"Resource '{self.name}' has no 'Properties' attribute."

    def get_properties_value(self) -> Dict[str, Any]:
        """Get the properties of the resource.

        Returns:
            Dict[str, Any]: The properties of the resource.
        """
        self.has_properties()

        properties = self.data["Properties"]

        return properties

    # may need to use somekinda function dispatch to allow multiple checks for different types
    def assert_propeties_is(self, properties: Dict[str, Any]):
        """Assert that the properties of the resource is equal to the given properties.

        Args:
            properties (Dict[str, Any]): The properties to compare the resource properties to.
        """
        actual_properties = self.get_properties_value()

        assert (
            properties == actual_properties
        ), f"Resource '{self.name}' actual properties did not match input properties"

    # Technically a property is an attribute, but I think users will understand this better
    def assert_has_property(self, property_name: str):
        """Assert that the resource has a property with the given name.

        Args:
            property_name (str): The name of the property to check for.
        """
        properties = self.get_properties_value()

        assert (
            property_name in properties
        ), f"Resource '{self.name}' has no property {property_name}."

    def get_property_value(self, property_name: str):
        """Get the value of the property with the given name.

        Args:
            property_name (str): The name of the property to get the value of.

        Returns:
            Any: The value of the property.
        """
        self.assert_has_property(property_name)

        properties = self.get_properties_value()

        return properties[property_name]

    def assert_property_has_value(self, property_name: str, property_value: Any):
        """Assert that the property with the given name has the given value.

        Args:
            property_name (str): The name of the property to check.
            property_value (Any): The value to compare the property value to.
        """
        self.assert_has_property(property_name)

        actual_property_value = self.get_property_value(property_name)

        assert actual_property_value == property_value, (
            f"Resource '{self.name}' property '{property_name}' value "
            f"'{actual_property_value}' did not match input value '{property_value}'."
        )

    def assert_property_value_matches_pattern(self, property_name: str, pattern: str):
        """Assert that the property with the given name has a value matching
         the supplied pattern.

        Args:
            property_name (str): The name of the property to check.
            pattern (str): The regex to compare the property value to.
        """
        actual_property_value = self.get_property_value(property_name)

        assert re.match(pattern, actual_property_value), (
            f"Resource '{self.name}' property '{property_name}' value "
            f"'{actual_property_value}' did not match expected pattern '{pattern}'."
        )

    def assert_has_tag(self, tag_name: str, tag_property_name: str = "Tags"):
        """Assert that the resource has a Tag with the given name.

        Args:
            tag_name (str): The name of the tag to check for.
            tag_property_name (str): The name of the property containing
                                     the tags. Most commonly this is the
                                     default of "Tags", but can change for
                                     some resource types.
        """

        tag_value = self.get_tag_value(tag_name, tag_property_name)

        assert (
            tag_value is not None
        ), f"Resource '{self.name}' has no tag {tag_property_name}."

    def get_tag_value(self, tag_name: str, tag_property_name: str = "Tags"):
        """Get the value of the tag with the given name.

        Args:
            tag_name (str): The name of the tag to get the value of.
            tag_property_name(str): The name of the tag field to get
                                    the tag from. This will default to
                                    Tag, but some resources use a different
                                    name.

        Returns:
            Any: The value of the tag.
        """
        self.assert_has_property(tag_property_name)

        properties = self.get_properties_value()
        tags = properties[tag_property_name]

        # There are basically two formats that Tags can be represented in (with
        # the correct one being determined by the resource type). These are:
        #
        # Tags:
        #   - Key: <key>
        #     Value: <value>
        #
        # Tags:
        #   <key>: <value>
        #
        # In this library we are not going to keep track of which is valid for which type
        # (that is more for a linter), but will support parsing both formats.

        if isinstance(tags, list):
            # Tags are in this format
            #   - Key: <key>
            #     Value: <value>
            #
            # Convert into the other format for easier handling
            tags = {tag["Key"]: tag["Value"] for tag in tags}

        return tags.get(tag_name)

    def assert_tag_has_value(
        self, tag_name: str, tag_value: str, tag_property_name: str = "Tags"
    ):
        """Assert that the Tag with the given name has the given value.

        Args:
            tag_name (str): The name of the tag to check.
            tag_value (str): The value to compare the tag value to.
            tag_property_name(str): The name of the tag field to get
                                    the tag from. This will default to
                                    Tag, but some resources use a different
                                    name.
        """

        actual_tag_value = self.get_tag_value(tag_name, tag_property_name)

        assert actual_tag_value == tag_value, (
            f"Resource '{self.name}' tag '{tag_name}' value "
            f"'{actual_tag_value}' did not match input value '{tag_value}'."
        )

    def assert_tag_value_matches_pattern(
        self, tag_name: str, pattern: str, tag_property_name: str = "Tags"
    ):
        """Assert that the Tag with the given name has a value matching
         the supplied pattern.

        Args:
            tag_name (str): The name of the tag to check.
            pattern (str): The regex to compare the tag value to.
            tag_property_name(str): The name of the tag field to get
                                    the tag from. This will default to
                                    Tag, but some resources use a different
                                    name.
        """

        actual_tag_value = self.get_tag_value(tag_name, tag_property_name)

        assert re.match(pattern, actual_tag_value), (
            f"Resource '{self.name}' tag '{tag_name}' value "
            f"'{actual_tag_value}' did not match expected pattern '{pattern}'."
        )
