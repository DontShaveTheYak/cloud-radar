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
        acutal_type = self.get_type_value()

        assert (
            type == acutal_type
        ), f"Resource '{self.name}' type {acutal_type} did not match input {type}"

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
        acutal_properties = self.get_properties_value()

        assert (
            properties == acutal_properties
        ), f"Resource '{self.name}' acutal properties did not match input properties"

    # Technically a propery is an attribute, but I think users will understand this better
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
