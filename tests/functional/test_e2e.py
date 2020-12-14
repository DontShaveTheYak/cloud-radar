from pathlib import Path

import pytest

from cloud_radar import Test

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def template_dir():
    return Path(__file__).parent / "./templates"


@pytest.fixture()
def default_config():
    config = {
        "project": {
            "name": "taskcat-test-logbucket",
            "regions": ["us-west-1", "us-west-2"],
        },
        "tests": {
            "log-bucket": {
                "template": "./log_bucket.yaml",
                "parameters": {
                    "BucketPrefix": "taskcat-$[taskcat_random-string]",
                    "KeepBucket": "FALSE",
                },
            }
        },
    }

    return config


def test_config_file(template_dir):

    test_dir = template_dir / "log_bucket"

    with Test("log-bucket", test_dir.resolve()) as stacks:

        for stack in stacks:

            print(f"Testing {stack.name}")

            bucket_name = ""

            for output in stack.outputs:

                if output.key == "LogsBucketName":
                    bucket_name = output.value
                    break

            assert "logs" in bucket_name

            assert stack.region.name in bucket_name

            print(f"Created bucket: {bucket_name}")


def test_input_file(template_dir, default_config):

    test_dir = template_dir / "log_bucket"

    log_test = Test("log-bucket", test_dir.resolve(), config_input=default_config)

    with log_test as stacks:
        for stack in stacks:
            assert (
                "us-east" not in stack.region.name
            ), "input_config should overide config file"


def test_retain_bucket(template_dir, default_config):

    default_config["tests"]["log-bucket"]["parameters"]["KeepBucket"] = "TRUE"

    test_dir = template_dir / "log_bucket"

    log_test = Test("log-bucket", test_dir.resolve(), config_input=default_config)

    with log_test as stacks:
        pass

    for stack in stacks:
        session = stack.region.session

        s3 = session.resource("s3")

        for output in stack.outputs:

            if output.key == "LogsBucketName":
                bucket = s3.Bucket(output.value)
                bucket.wait_until_exists()
                bucket.delete()
                bucket.wait_until_not_exists()
                break
