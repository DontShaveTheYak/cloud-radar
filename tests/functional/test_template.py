from pathlib import Path

import pytest

from cloud_radar.unit_test import Template


@pytest.fixture
def template():
    template_path = Path(__file__).parent / "../templates/log_bucket/log_bucket.yaml"

    return Template(template_path.resolve())


def test_log_defaults(template):

    result = template.render({"BucketPrefix": "testing"})

    assert "LogsBucket" in result["Resources"]

    bucket_name = result["Resources"]["LogsBucket"]["Properties"]["BucketName"]

    assert "us-east-1" in bucket_name


def test_log_retain(template):

    result = template.render(
        {"BucketPrefix": "testing", "KeepBucket": "TRUE"}, region="us-west-2"
    )

    assert "LogsBucket" not in result["Resources"]

    bucket_name = result["Resources"]["RetainLogsBucket"]["Properties"]["BucketName"]

    assert "us-west-2" in bucket_name
