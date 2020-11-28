from contextlib import contextmanager
from typing import Iterator

from taskcat._cfn.stack import Stacks

from .manager import TestManager


@contextmanager
def Test(
    test_name: str,
    project_dir: str,
    config_input: dict = None,
    config_file: str = "./.taskcat.yml",
    regions: str = "ALL",
    wait_for_delete: bool = False,
) -> Iterator[Stacks]:
    """Create Stacks for a Taskcat test and return the stacks.

    Must pass in a Taskcat configuration as either a dictionary or file.

    Args:
        test_name (str): The name of the test from the Taskcat config file.
        project_dir (str): The directory that contains your Taskcat config and Cloudformation files.
        config_input (dict, optional): Taskcat config file in the form of a dictionary. Defaults to None.
        config_file (str, optional): The name of the Taskcat config file. Defaults to "./.taskcat.yml".
        regions (str, optional): Override the regions defined in the config file. Defaults to "ALL".
        wait_for_delete (bool, optional): Wait until stacks have been deleted. Defaults to False.

    Yields:
        Iterator[Stacks]: The stacks created for the tests.
    """  # noqa: B950
    print(f"Creating stacks for test {test_name}")

    sm = TestManager(
        test_name, project_dir, config_input=config_input, config_file=config_file
    )

    sm.create(regions)
    try:
        yield sm.stacks
    finally:
        print("Deleting Stacks")
        sm.delete(wait_for_delete)
