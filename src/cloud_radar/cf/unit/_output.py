from collections import UserDict
from typing import Any, Dict


class Output(UserDict):
    def __init__(self, name: str, output_data: Dict[str, Any]) -> None:
        super().__init__(output_data)
        self.name = name

    def has_value(self):
        """Check if the output has a value."""
        assert "Value" in self.data, f"Output '{self.name}' has no value."

    def get_value(self) -> str:
        """Get the value of the output.

        Returns:
            str: The value of the output.
        """
        self.has_value()

        return self.data["Value"]

    def assert_value_is(self, value: Any):
        """Assert that the value of the output is equal to the given value.

        Args:
            value (Any): The value to compare the output value to.
        """
        acutal_value = self.get_value()

        assert (
            value == acutal_value
        ), f"Output '{self.name}' actual value did not match input value."

    def has_export(self):
        """Check if the output has an export."""
        assert (
            "Export" in self.data and "Name" in self.data["Export"]
        ), f"Output '{self.name}' has no export."

    def get_export(self) -> str:
        """Get the export name of the output.

        Returns:
            str: The export name of the output.
        """
        self.has_export()

        return self.data["Export"]["Name"]

    def assert_export_is(self, export_name: str):
        """Assert that the export name of the output is equal to the given export name.

        Args:
            export_name (str): The export name to compare the output export name to.
        """
        actual_export = self.get_export()

        assert (
            actual_export == export_name
        ), f"Output '{self.name}' export value doesn't match user input."
