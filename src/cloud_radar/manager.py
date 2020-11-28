import uuid
from pathlib import Path
from typing import List

from taskcat._cfn.threaded import Stacker
from taskcat._cfn_lint import Lint as TaskCatLint
from taskcat._cli_core import GLOBAL_ARGS
from taskcat._cli_modules import Test
from taskcat._cli_modules import test as test_utils
from taskcat._config import Config
from taskcat._lambda_build import LambdaBuild
from taskcat._s3_stage import stage_in_s3
from taskcat._tui import TerminalPrinter
from taskcat.exceptions import TaskCatException


class TestManager(Test):
    """
    Class to create and manage test stacks.
    """

    def __init__(
        self,
        test_name: str,
        project_dir: str,
        config_input: dict = None,
        config_file: str = "./.taskcat.yml",
    ) -> None:
        """Creates a TestManager that is capable of creating and deleting stacks.

        Must pass in a Taskcat configuration as either a dictionary or file.

        Args:
            test_name (str): The name of the test from the Taskcat config file.
            project_dir (str): The directory that contains your Taskcat config and Cloudformation files.
            config_input (dict, optional): Taskcat config file in the form of a dictionary. Defaults to None.
            config_file (str, optional): The name of the Taskcat config file. Defaults to "./.taskcat.yml".
        """  # noqa: B950
        self.uid = uuid.uuid4()
        self.test_name = test_name
        self.project_dir = project_dir

        project_root_path: Path = Path(self.project_dir).expanduser().resolve()
        args = test_utils._build_args(False, "ALL", GLOBAL_ARGS.profile)

        if config_input:
            sources = [
                {"source": "Manual", "config": config_input},
                {"source": "CliArgument", "config": args},
            ]

            config = Config(
                uid=self.uid, project_root=project_root_path, sources=sources
            )

        else:
            input_file_path: Path = project_root_path / config_file

            config = Config.create(
                project_root=project_root_path,
                project_config_path=input_file_path,
                args=args,
            )

        self.config = config

    def create(self, regions: str = "ALL") -> None:
        """Creates the stacks to be tested.

        Args:
            regions (str, optional): Override the regions defined in the config file. Defaults to "ALL".

        Raises:
            TaskCatException: If linting fails or a stack fails to create successfully.
        """  # noqa: B950

        boto3_cache = test_utils.Boto3Cache()

        test_utils._trim_regions(regions, self.config)
        test_utils._trim_tests(self.test_name, self.config)

        templates = self.config.get_templates()
        self.buckets = self.config.get_buckets(boto3_cache)

        lint = TaskCatLint(self.config, templates)
        errors = lint.lints[1]
        lint.output_results()
        if errors or not lint.passed:
            raise TaskCatException("Lint failed with errors")

        if self.config.config.project.package_lambda:
            LambdaBuild(self.config, self.config.project_root)

        stage_in_s3(
            self.buckets, self.config.config.project.name, self.config.project_root
        )

        regions = self.config.get_regions(boto3_cache)
        parameters = self.config.get_rendered_parameters(
            self.buckets, regions, templates
        )

        tests = self.config.get_tests(templates, regions, self.buckets, parameters)

        self.test_definition = Stacker(
            self.config.config.project.name,
            tests,
            uid=self.uid,
            shorten_stack_name=self.config.config.project.shorten_stack_name,
        )

        self.test_definition.create_stacks()

        terminal_printer = TerminalPrinter(minimalist=True)
        terminal_printer.report_test_progress(stacker=self.test_definition)

        status = self.test_definition.status()
        if len(status["FAILED"]) > 0:
            raise TaskCatException(
                f'One or more stacks failed tests: {status["FAILED"]}'
            )

        self.stacks = self.test_definition.stacks

    def delete(self, wait_for_delete: bool = False) -> None:
        """Delete the stacks created for the test.

        Args:
            wait_for_delete (bool, optional): Wait until stacks have been deleted. Defaults to False.
        """  # noqa: B950
        self.test_definition.delete_stacks()

        if wait_for_delete:
            terminal_printer = TerminalPrinter(minimalist=True)
            terminal_printer.report_test_progress(stacker=self.test_definition)

        deleted: List[str] = []
        for test in self.buckets.values():
            for bucket in test.values():
                if (bucket.name not in deleted) and not bucket.regional_buckets:
                    bucket.delete(delete_objects=True)
                    deleted.append(bucket.name)
