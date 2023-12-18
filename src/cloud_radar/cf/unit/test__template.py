# Just a note that GitHub Copilot generated this entire file, first try
import pytest

from cloud_radar.cf.unit import functions
from cloud_radar.cf.unit._template import Template


def test_load_allowed_functions_no_transforms():
    template = Template({})
    result = template.load_allowed_functions()
    assert result == functions.ALL_FUNCTIONS


def test_load_allowed_functions_single_transform():
    template = Template({"Transform": "AWS::Serverless-2016-10-31"})
    result = template.load_allowed_functions()
    expected = {
        **functions.ALL_FUNCTIONS,
        **functions.TRANSFORMS["AWS::Serverless-2016-10-31"],
    }
    assert result == expected


def test_load_allowed_functions_multiple_transforms():
    template = Template({"Transform": ["AWS::Serverless-2016-10-31", "AWS::Include"]})
    result = template.load_allowed_functions()
    expected = {
        **functions.ALL_FUNCTIONS,
        **functions.TRANSFORMS["AWS::Serverless-2016-10-31"],
        **functions.TRANSFORMS["AWS::Include"],
    }
    assert result == expected


def test_load_allowed_functions_invalid_transform():
    template = Template({"Transform": "InvalidTransform"})
    with pytest.raises(ValueError):
        template.load_allowed_functions()


def test_load_allowed_functions_invalid_transforms():
    template = Template(
        {"Transform": ["AWS::Serverless-2016-10-31", "InvalidTransform"]}
    )
    with pytest.raises(ValueError):
        template.load_allowed_functions()
