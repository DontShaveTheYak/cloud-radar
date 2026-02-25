from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    # Only for static typing — not required at runtime
    from taskcat.testing import CFNTest  # noqa: F401

Template = Union[str, Path]
Parameters = Optional[Dict[str, Any]]
Regions = Optional[List[str]]

try:
    from taskcat.testing import CFNTest as _CFNTestBase
except ImportError:
    _CFNTestBase = None


def _raise_taskcat_missing() -> None:
    raise ImportError(
        "cloud-radar E2E stack support requires 'taskcat'.\n\n"
        "Install it with:\n"
        "  pip install cloud-radar[e2e]\n"
        "or add 'taskcat' to your environment."
    )


def _create_tc_config() -> Dict[str, Any]:
    caller = sys._getframe(2)

    caller_name = caller.f_code.co_name

    test_name = caller_name.replace("_", "-")

    config = {
        "project": {
            "name": f"taskcat-{test_name}",
        },
        "tests": {"default": {}},
    }

    return config


if _CFNTestBase is None:

    class Stack:  # type: ignore[no-redef]
        """
        Placeholder Stack when taskcat is not installed.
        Raises a helpful error on instantiation.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _raise_taskcat_missing()

else:

    class Stack(_CFNTestBase):  # type: ignore[no-redef]
        def __init__(
            self,
            template: Template,
            parameters: Parameters = None,
            regions: Regions = None,
        ):
            """Tests Cloudformation template by making sure the stack can properly deploy
            in the specified regions.

            Args:
                template (Union[str, Path]): The path to the template.
                parameters (Optional[Dict[str, Any]]): The parameters names and values.
                regions (Optional[List[str]]): List of regions. Default is 'us-east-1'.
            """

            if not regions:
                regions = ["us-east-1"]

            region_csv = ",".join(regions)

            if not isinstance(template, Path):
                template = Path(template)

            config = _create_tc_config()

            config["project"]["regions"] = regions
            config["tests"]["default"]["template"] = str(template.resolve())

            if parameters:
                config["tests"]["default"]["parameters"] = parameters

            test = _CFNTestBase.from_dict(
                config, project_root=str(template.resolve().parent), regions=region_csv
            )

            super().__init__(test.config, regions=region_csv)
