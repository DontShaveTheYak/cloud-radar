class Condition:
    def __init__(self, name: str, condition_value: bool) -> None:
        self.name = name
        self.value = condition_value

    def assert_value_is(self, value: bool):
        """Tests if the condition value is equal to the given value.

        Args:
            value (bool): The value to test against.
        """
        assert (
            value is self.value
        ), f"Condition '{self.name}' is {self.value} not {value}."

    def get_value(self) -> bool:
        """Returns the value of the condition.

        Returns:
            bool: The value of the condition.
        """
        return self.value

    def __eq__(self, other) -> bool:
        return self.value == other
