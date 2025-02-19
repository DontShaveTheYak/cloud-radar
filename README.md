<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Python][py-versions-shield]][pypi-url]
[![Latest][version-shield]][pypi-url]
[![Tests][test-shield]][test-url]
[![Coverage][codecov-shield]][codecov-url]
[![License][license-shield]][license-url]
<!-- [![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url] -->

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <!-- <a href="https://github.com/DontShaveTheYak/cloud-radar">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a> -->

  <h3 align="center">Cloud-Radar</h3>

  <p align="center">
    Write unit and functional tests for AWS Cloudformation.
    <!-- <br />
    <a href="https://github.com/DontShaveTheYak/cloud-radar"><strong>Explore the docs »</strong></a>
    <br /> -->
    <br />
    <!-- <a href="https://github.com/DontShaveTheYak/cloud-radar">View Demo</a>
    · -->
    <a href="https://github.com/DontShaveTheYak/cloud-radar/issues">Report Bug</a>
    ·
    <a href="https://github.com/DontShaveTheYak/cloud-radar/issues">Request Feature</a>
    ·
    <a href="https://la-tech.co/post/hypermodern-cloudformation/getting-started/">Guide</a>
  </p>
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>

## About The Project

<!-- [![Product Name Screen Shot][product-screenshot]](https://example.com) -->

Cloud-Radar is a python module that allows testing of Cloudformation Templates/Stacks using Python.

### Unit Testing

You can now unit test the logic contained inside your Cloudformation template. Cloud-Radar takes your template, the desired region and some parameters. We render the template into its final state and pass it back to you.

You can Test:
* That Conditionals in your template evaluate to the correct value.
* Conditional resources were created or not.
* That resources have the correct properties.
* That resources are named as expected because of `!Sub`.

You can test all this locally without worrying about AWS Credentials.

A number of these tests can be configured in a common way to apply to all templates through the use of the [hooks](./examples/unit/hooks/README.md) functionality.

### Functional Testing

This project is a wrapper around Taskcat. Taskcat is a great tool for ensuring your Cloudformation Template can be deployed in multiple AWS Regions. Cloud-Radar enhances Taskcat by making it easier to write more complete functional tests.

Here's How:
* You can interact with the deployed resources directly with tools you already know like boto3.
* You can control the lifecycle of the stack. This allows testing if resources were retained after the stacks were deleted.
* You can run tests without hardcoding them in a taskcat config file.

This project is new and it's possible not all features or functionality of Taskcat/Cloudformation are supported (see [Roadmap](#roadmap)). If you find something missing or have a use case that isn't covered then please let me know =)

### Built With

* [Taskcat](https://github.com/aws-quickstart/taskcat)
* [cfn_tools from cfn-flip](https://github.com/awslabs/aws-cfn-template-flip)

## Getting Started

Cloud-Radar is available as an easy to install pip package.

### Prerequisites

Cloud-Radar requires python >= 3.8

### Installation

1. Install with pip.
   ```sh
   pip install cloud-radar
   ```

## Usage
<details>
<summary>Unit Testing <span style='font-size: .67em'>(Click to expand)</span></summary>

Using Cloud-Radar starts by importing it into your test file or framework. We will use this [Template](./tests/templates/log_bucket/log_bucket.yaml) for an example shown below. More scenario based examples are currently being built up in the [examples/unit](./examples/unit) directory of this project.

```python
from pathlib import Path
from cloud_radar.cf.unit import Template

template_path = Path("tests/templates/log_bucket/log_bucket.yaml")

# template_path can be a str or a Path object
template = Template.from_yaml(template_path.resolve())

params = {"BucketPrefix": "testing", "KeepBucket": "TRUE"}

# parameters and region are optional arguments.
stack = template.create_stack(params, region="us-west-2")

stack.no_resource("LogsBucket")

bucket = stack.get_resource("RetainLogsBucket")

assert "DeletionPolicy" in bucket

assert bucket["DeletionPolicy"] == "Retain"

bucket_name = bucket.get_property_value("BucketName")

assert "us-west-2" in bucket_name
```

The AWS [pseudo parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/pseudo-parameter-reference.html) are all class attributes and can be modified before rendering a template.
```python
# The value of 'AWS::AccountId' in !Sub "My AccountId is ${AWS::AccountId}" can be changed:
Template.AccountId = '8675309'
```
_Note: Region should only be changed to change the default value. To change the region during testing pass the desired region to render(region='us-west-2')_

The default values for pseudo parameters:

| Name             | Default Value   |
| ---------------- | --------------- |
| AccountId        | "555555555555"  |
| NotificationARNs | []              |
| **NoValue**      | ""              |
| **Partition**    | "aws"           |
| Region           | "us-east-1"     |
| StackId          | (generated based on other values)              |
| StackName    | "my-cloud-radar-stack"              |
| **URLSuffix**    | "amazonaws.com" |
_Note: Bold variables are not fully implemented yet see the [Roadmap](#roadmap)_

At the point of creating the `Template` instance additional configuration is required to be provided if you are using certain approaches to resolving values.

If you use [Fn::ImportValue](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-importvalue.html), a dictionary of key/value pairs is required containing all the keys that your template uses. If an import name is referenced by the template which is not included in this dictionary, an error will be raised.

```
imports = {
  "FakeKey": "FakeValue"
}

template = Template(template_content, imports=imports)
```

If you use [Dynamic References](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html), a dictionary containing the service and key/value pairs is required containing all the dynamic references that your template uses. If a dynamic reference is included in the template and not contained in the configuration object, an error will be raised.

```
template_content = {
    "Resources": {
        "Foo": {
            "Type": "AWS::IAM::Policy",
            "Properties": {
                "PolicyName": (
                    "mgt-{{resolve:ssm:/account/current/short_name}}-launch-role-pol"
                ),
            },
        },
    },
}

dynamic_references = {
  "ssm": {
    "/account/current/short_name": "dummy"
  }
}

template = Template(template_content, dynamic_references=dynamic_references)
```

There are cases where the default behaviour of our `Ref` and `GetAtt` implementations may not be sufficient and you need a more accurate returned value. When unit testing there are no real AWS resources created, and cloud-radar does not attempt to realistically generate attribute values - a string is always returned. For `Ref` this is the logical resource name, for `GetAtt` this is `<logical resource name>.<attribute name>`. This works good enough most of the time, but there are some cases where if you are attempting to apply intrinsic functions against these value it needs to be more correct. When this occurs, you can add Metadata to the template to provide test values to use.

```
Resources:
  MediaPackageV2Channel:
    Type: AWS::MediaPackageV2::Channel
    Metadata:
      Cloud-Radar:
        ref: arn:aws:mediapackagev2:region:AccountId:ChannelGroup/ChannelGroupName/Channel/ChannelName
        attribute-values:
        # Default behaviour of a string is not good enough here, the attribute value is expected to be a List.
          IngestEndpointUrls:
            - http://one.example.com
            - http://two.example.com
    Properties:
      ChannelGroupName: dev_video_1
      ChannelName: !Sub ${AWS::StackName}-MediaPackageChannel
```
If you are unable to modify the template itself, it is also possible to inject this metadata as part of the unit test. See [this test case](./tests/test_cf/test_unit/test_functions_ref.py) for an example.

A real unit testing example using Pytest can be seen [here](./tests/test_cf/test_examples/test_unit.py)

</details>

<details>
<summary>Functional Testing <span style='font-size: .67em'>(Click to expand)</span></summary>
Using Cloud-Radar starts by importing it into your test file or framework.

```python
from pathlib import Path

from cloud_radar.cf.e2e import Stack

# Stack is a context manager that makes sure your stacks are deleted after testing.
template_path = Path("tests/templates/log_bucket/log_bucket.yaml")
params = {"BucketPrefix": "testing", "KeepBucket": "False"}
regions = ['us-west-2']

# template_path can be a string or a Path object.
# params can be optional if all your template params have default values
# regions can be optional, default region is 'us-east-1'
with Stack(template_path, params, regions) as stacks:
    # Stacks will be created and returned as a list in the stacks variable.

    for stack in stacks:
        # stack will be an instance of Taskcat's Stack class.
        # It has all the expected properties like parameters, outputs and resources

        print(f"Testing {stack.name}")

        bucket_name = ""

        for output in stack.outputs:

            if output.key == "LogsBucketName":
                bucket_name = output.value
                break

        assert "logs" in bucket_name

        assert stack.region.name in bucket_name

        print(f"Created bucket: {bucket_name}")

# Once the test is over then all resources will be deleted from your AWS account.
```

You can use taskcat [tokens](https://aws.amazon.com/blogs/infrastructure-and-automation/a-deep-dive-into-testing-with-taskcat/) in your parameter values.

```python
parameters = {
  "BucketPrefix": "taskcat-$[taskcat_random-string]",
  "KeepBucket": "FALSE",
}
```

You can skip the context manager. Here is an example for `unittest`

```python
import unittest

from cloud-radar.cf.e2e import Stack

class TestLogBucket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        template_path = Path("tests/templates/log_bucket/log_bucket.yaml")
        cls.test = Stack(template_path)
        cls.test.create()

    @classmethod
    def tearDownClass(cls):
        cls.test.delete()

    def test_bucket(self):
        stacks = self.__class__.test.stacks

        for stack in stacks:
            # Test
```

All the properties and methods of a [stack instance](https://github.com/aws-quickstart/taskcat/blob/main/taskcat/_cfn/stack.py#L188).

A real functional testing example using Pytest can be seen [here](./tests/test_cf/test_examples/test_functional.py)

</details>

## Roadmap

### Project
- Add Logo
- Easier to pick regions for testing

### Unit
- Add full functionality to pseudo variables.
  * Variables like `Partition`, `URLSuffix` should change if the region changes.
- Handle References to resources that shouldn't exist.
  * It's currently possible that a `!Ref` to a Resource stays in the final template even if that resource is later removed because of a conditional.

### Functional
- Add the ability to update a stack instance to Taskcat.

See the [open issues](https://github.com/DontShaveTheYak/cloud-radar/issues) for a list of proposed features (and known issues).

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

This project uses poetry to manage dependencies and pre-commit to run formatting, linting and tests. You will need to have both installed to your system as well as python 3.12.

1. Fork the Project
2. Setup environment (`poetry install`)
3. Setup commit hooks (`pre-commit install`)
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the Apache-2.0 License. See [LICENSE.txt](./LICENSE.txt) for more information.

## Contact

Levi - [@shady_cuz](https://twitter.com/shady_cuz)

<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements
* [Taskcat](https://aws-quickstart.github.io/taskcat/)
* [Hypermodern Python](https://cjolowicz.github.io/posts/hypermodern-python-01-setup/)
* [Best-README-Template](https://github.com/othneildrew/Best-README-Template)
* [David Hutchison (@dhutchison)](https://github.com/dhutchison) - He was the first contributor to this project and finished the last couple of features to make this project complete. Thank you!

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[python-shield]: https://img.shields.io/pypi/pyversions/cloud-radar?style=for-the-badge
[py-versions-shield]: https://img.shields.io/pypi/pyversions/cloud-radar?style=for-the-badge
[version-shield]: https://img.shields.io/pypi/v/cloud-radar?label=latest&style=for-the-badge
[pypi-url]: https://pypi.org/project/cloud-radar/
[test-shield]: https://img.shields.io/github/actions/workflow/status/DontShaveTheYak/cloud-radar/test.yml?label=Tests&style=for-the-badge
[test-url]: https://github.com/DontShaveTheYak/cloud-radar/actions?query=workflow%3ATests+branch%3Amaster
[codecov-shield]: https://img.shields.io/codecov/c/gh/DontShaveTheYak/cloud-radar?color=green&style=for-the-badge&token=NE5C92139X
[codecov-url]: https://codecov.io/gh/DontShaveTheYak/cloud-radar
[contributors-shield]: https://img.shields.io/github/contributors/DontShaveTheYak/cloud-radar.svg?style=for-the-badge
[contributors-url]: https://github.com/DontShaveTheYak/cloud-radar/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/DontShaveTheYak/cloud-radar.svg?style=for-the-badge
[forks-url]: https://github.com/DontShaveTheYak/cloud-radar/network/members
[stars-shield]: https://img.shields.io/github/stars/DontShaveTheYak/cloud-radar.svg?style=for-the-badge
[stars-url]: https://github.com/DontShaveTheYak/cloud-radar/stargazers
[issues-shield]: https://img.shields.io/github/issues/DontShaveTheYak/cloud-radar.svg?style=for-the-badge
[issues-url]: https://github.com/DontShaveTheYak/cloud-radar/issues
[license-shield]: https://img.shields.io/github/license/DontShaveTheYak/cloud-radar.svg?style=for-the-badge
[license-url]: https://github.com/DontShaveTheYak/cloud-radar/blob/master/LICENSE.txt
[product-screenshot]: images/screenshot.png
