from collections import UserDict
from typing import Any, Dict, List


class Parameter(UserDict):
    def __init__(self, name: str, parameter_data: Dict[str, Any]) -> None:
        super().__init__(parameter_data)
        self.name = name

    def has_default(self):
        """Check if the parameter has a default value."""
        assert "Default" in self.data, f"Parameter '{self.name}' has no default value."

    def has_no_default(self):
        """Check if the parameter has no default value."""
        assert (
            "Default" not in self.data
        ), f"Parameter '{self.name}' has a default value."

    def assert_default_is(self, value: Any):
        """Assert that the default value of the parameter is equal to the given value.

        Args:
            value (Any): The value to compare the parameter default value to.
        """
        acutal_value = self.get_default_value()

        assert (
            value == acutal_value
        ), f"Parameter '{self.name}' has default value '{acutal_value}', expected '{value}'."

    def get_default_value(self):
        """Get the default value of the parameter.

        Returns:
            Any: The default value of the parameter.
        """
        self.has_default()

        default = self.data["Default"]

        return default

    # This check should be moved to inside the resolver?
    def has_type(self):
        """Check if the parameter has a type."""
        assert "Type" in self.data

    def assert_type_is(self, type: str):
        """Assert that the type of the parameter is equal to the given type.

        Args:
            type (str): The type to compare the parameter type to.
        """
        acutal_type = self.get_type_value()

        assert type == acutal_type, f"Parameter '{self.name}' has type '{acutal_type}'."

    def get_type_value(self) -> str:
        """Get the type of the parameter.

        Returns:
            str: The type of the parameter.
        """
        type = self.data.get("Type")

        if not type:
            assert False, f"Parameter '{self.name}' has no type value."  # noqa: B011

        return type

    def has_allowed_values(self):
        """Check if the parameter has allowed values."""
        assert (
            "AllowedValues" in self.data
        ), f"Parameter '{self.name}' has no allowed values."

    def assert_allowed_values_is(self, allowed_values: List[Any]):
        """Assert that the allowed values of the parameter is equal to the given allowed values.

        Args:
            allowed_values (List[Any]): The allowed values to compare the parameter
            allowed values to.
        """
        actual_allowed_values = self.get_allowed_values()

        assert set(allowed_values) == set(
            actual_allowed_values
        ), f"Parameter '{self.name}' has allowed values '{actual_allowed_values}'."

    def get_allowed_values(self):
        """Get the allowed values of the parameter.

        Returns:
            List[Any]: The allowed values of the parameter.
        """
        self.has_allowed_values()

        actual_allowed_values: List[Any] = self.data["AllowedValues"]

        return actual_allowed_values
