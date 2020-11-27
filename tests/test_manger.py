from unittest.mock import ANY, MagicMock

import pytest

from cloud_radar import TestManager


@pytest.fixture
def mock_utils(mocker):
    mock = mocker.patch("cloud_radar.manager.test_utils")
    return mock


@pytest.fixture
def mock_config(mocker):
    mock = mocker.patch("cloud_radar.manager.Config")
    return mock


@pytest.fixture
def mock_lambda(mocker):
    mock = mocker.patch("cloud_radar.manager.LambdaBuild")
    return mock


@pytest.fixture
def mock_report(mocker):
    mock = mocker.patch("cloud_radar.manager.ReportBuilder")
    return mock


@pytest.fixture
def mock_lint(mocker):
    mock = mocker.patch("cloud_radar.manager.TaskCatLint")
    return mock


@pytest.fixture
def mock_stacker(mocker):
    mock = mocker.patch("cloud_radar.manager.Stacker")
    return mock


@pytest.fixture
def mock_stage(mocker):
    mock = mocker.patch("cloud_radar.manager.stage_in_s3")
    return mock


@pytest.fixture
def mock_test(mocker):
    mock = mocker.patch("cloud_radar.manager.Test")
    return mock


@pytest.fixture
def mock_exception(mocker):
    mock = mocker.patch("cloud_radar.manager.TaskCatException")
    return mock


@pytest.fixture
def mock_printer(mocker):
    mock = mocker.patch("cloud_radar.manager.TerminalPrinter")
    return mock


@pytest.fixture
def mock_delete(mocker):
    mock = mocker.patch("cloud_radar.manager.Test.clean")
    return mock


def test_default_values(mock_utils, mock_config):
    sm = TestManager("test", "../templates/audit_bucket")

    mock_utils._build_args.assert_called_once_with(False, "ALL", "default")
    mock_config.create.assert_called_once()

    assert sm.config is mock_config.create()

    mock_config.reset_mock()

    config = {"project": {}}

    sm = TestManager("test", "./", config_input=config)

    mock_config.assert_called_once_with(uid=sm.uid, project_root=ANY, sources=ANY)


def test_create(
    mock_utils, mock_config, mock_lint, mock_lambda, mock_stage, mock_stacker
):
    mock_lint.return_value.lints = [False, False]
    mock_lint.return_value.passed = True

    sm = TestManager("test", "../templates/audit_bucket")

    sm.create()

    mock_utils.Boto3Cache.assert_called_once()
    mock_utils._trim_regions.assert_called_once_with("ALL", sm.config)
    mock_utils._trim_tests.assert_called_once_with("test", sm.config)

    config = mock_config.create.return_value

    config.get_templates.assert_called_once()
    config.get_buckets.assert_called_once_with(mock_utils.Boto3Cache())
    config.get_regions.assert_called_once_with(mock_utils.Boto3Cache())
    config.get_rendered_parameters.assert_called_once_with(
        config.get_buckets(), config.get_regions(), config.get_templates()
    )
    config.get_tests.assert_called_once_with(
        config.get_templates(),
        config.get_regions(),
        config.get_buckets(),
        config.get_rendered_parameters(),
    )

    mock_lint.assert_called_with(sm.config, config.get_templates())
    mock_lint.return_value.output_results.assert_called_once()

    mock_lambda.assert_called_once_with(sm.config, sm.config.project_root)

    mock_stage.assert_called_once_with(
        config.get_buckets(), config.config.project.name, config.project_root
    )

    mock_stacker.assert_called_once_with(
        config.config.project.name,
        config.get_tests(),
        uid=sm.uid,
        shorten_stack_name=config.config.project.shorten_stack_name,
    )
    stacker = mock_stacker.return_value
    stacker.create_stacks.assert_called_once()
    stacker.status.assert_called()


def test_lint_failure(
    mock_utils,
    mock_config,
    mock_lint,
    mock_lambda,
    mock_stage,
    mock_stacker,
    mock_exception,
):
    mock_lint.return_value.lints = [False, True]
    mock_lint.return_value.passed = False

    sm = TestManager("test", "../templates/audit_bucket", "./.taskcat.yml")

    try:
        sm.create()
    except Exception:
        pass

    mock_exception.assert_called_once_with("Lint failed with errors")


def test_failed_stack(
    mock_utils,
    mock_config,
    mock_lint,
    mock_lambda,
    mock_stage,
    mock_stacker,
    mock_exception,
    mock_printer,
):
    mock_lint.return_value.lints = [False, False]
    mock_lint.return_value.passed = True
    mock_stacker.return_value.status.return_value = {"FAILED": ["stack-a"]}

    sm = TestManager("test", "../templates/audit_bucket", "./.taskcat.yml")

    try:
        sm.create()
    except Exception:
        pass

    mock_exception.assert_called_once_with(
        "One or more stacks failed tests: ['stack-a']"
    )


def test_delete(
    mock_config,
    mock_stacker,
):

    bucket_a = MagicMock()
    bucket_a.name = "Bucket-A"
    bucket_a.regional_buckets = False

    bucket_b = MagicMock()
    bucket_b.name = "Bucket-B"
    bucket_b.regional_buckets = True

    test_values = MagicMock()
    test_values.values.return_value = [bucket_a, bucket_b]

    mock_buckets = MagicMock()
    mock_buckets.values.return_value = [test_values]

    sm = TestManager("test", "../templates/audit_bucket", "./.taskcat.yml")

    sm.test_definition = mock_stacker()

    sm.buckets = mock_buckets
    sm.delete()

    stacker = mock_stacker.return_value
    stacker.delete_stacks.assert_called_once()

    bucket_a.delete.assert_called_once_with(delete_objects=True)
    bucket_b.delete.assert_not_called()


def test_delete_wait(
    mock_config,
    mock_printer,
    mock_stacker,
):
    mock_buckets = MagicMock()
    mock_buckets.values.return_value = []

    sm = TestManager("test", "../templates/audit_bucket", "./.taskcat.yml")

    sm.test_definition = mock_stacker()

    sm.buckets = mock_buckets
    sm.delete(True)

    mock_printer.assert_called_with(minimalist=True)

    printer = mock_printer.return_value

    printer.report_test_progress.assert_called_once_with(
        stacker=mock_stacker.return_value
    )
