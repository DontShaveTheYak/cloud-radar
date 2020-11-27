import pytest

from cloud_radar import Test


@pytest.fixture
def mock_manager(mocker):
    mock = mocker.patch("cloud_radar.context.TestManager")
    instance = mock.return_value
    instance.stacks = []

    return mock


def test_default_values(mock_manager):
    test = "test"
    path = "./"
    config_file = "./.taskcat.yml"
    config = None

    with Test(test, path) as stacks:  # noqa: F841
        mock_manager.assert_called_once_with(
            test, path, config_input=config, config_file=config_file
        )

    mock_manager.reset_mock()
    config = {"project": {}}

    with Test(test, path, config_input=config) as stacks:  # noqa: F841
        mock_manager.assert_called_once_with(
            test, path, config_input=config, config_file=config_file
        )


def test_returns_list(mock_manager):
    with Test("audit-bucket", "./") as stacks:
        assert isinstance(stacks, list)


def test_cleans_up(mock_manager):

    try:
        with Test("audit-bucket", "./") as stacks:  # noqa: F841
            raise Exception("Test")
    except Exception:
        assert mock_manager.return_value.create.called
        assert mock_manager.return_value.delete.called
