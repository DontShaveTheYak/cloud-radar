<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Python][python-shield]][pypi-url]
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
    Write functional tests for multi-region Cloudformation stacks.
    <!-- <br />
    <a href="https://github.com/DontShaveTheYak/cloud-radar"><strong>Explore the docs »</strong></a>
    <br /> -->
    <br />
    <!-- <a href="https://github.com/DontShaveTheYak/cloud-radar">View Demo</a>
    · -->
    <a href="https://github.com/DontShaveTheYak/cloud-radar/issues">Report Bug</a>
    ·
    <a href="https://github.com/DontShaveTheYak/cloud-radar/issues">Request Feature</a>
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

Cloud-Radar is a python module that allows testing of Cloudformation Templates using Python.

### Unit Testing

You can now unit test the logic contained inside your Cloudformation template. Cloud-Radar takes your template, the desired region and some parameters. We render the template into its final state and pass it back to you.

You can Test:
* That Conditionals in your template evaluate to the correct behavior.
* Conditional resources were created or not.
* That resources have the correct properties.
* That resources are named as expected because of `!Sub`.

You can test all this locally without worrying about AWS Credentials.

### Functional Testing

This project is a wrapper around Taskcat. Taskcat is a great tool for ensuring your Cloudformation Template can be deployed in multiple AWS Regions. Cloud-Radar enhances Taskcat by making it easier to write more complete functional tests.

Here's How:
* You can interact with the deployed resources directly with tools you already know like boto3.
* You can control the lifecycle of the stack. This allows testing if resources were retained after the stacks were deleted.
* You can dynamically generate taskcat projects, tests and template parameters without hardcoding them in a config file.

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
<summary>Unit Testing</summary>

Using Cloud-Radar starts by importing it into your test file or framework. We will use this [Template](./tests/templates/log_bucket/log_bucket.yaml) as an example.

```python
from cloud_radar.unit_test import Template

template_path = Path(__file__).parent / "../templates/log_bucket/log_bucket.yaml"

# template_path can be a str or a Path object
template = Template.from_yaml(template_path.resolve())

params = {"BucketPrefix": "testing", "KeepBucket": "TRUE"}

# parameters and region are optional arguments.
result = template.render(params, region="us-west-2")

assert "LogsBucket" not in result["Resources"]

bucket = result["Resources"]["RetainLogsBucket"]

assert "DeletionPolicy" in bucket

assert bucket["DeletionPolicy"] == "Retain"

bucket_name = bucket["Properties"]["BucketName"]

assert "us-west-2" in bucket_name
```

The AWS pseudo variables are all class attributes and can be modified before rendering a template.
```python
# The value of 'AWS::AccountId' in !Sub "My AccountId is ${AWS::AccountId}" can be changed:
Template.AccountId = '8675309'
```
_Note: Region should only be changed to change the default value. To change the region during testing pass the desired region to render(region='us-west-2')_

The default values for psedo variables:

| Name             | Default Value   |
| ---------------- | --------------- |
| AccountId        | "555555555555"  |
| NotificationARNs | []              |
| **NoValue**      | ""              |
| **Partition**    | "aws"           |
| Region           | "us-east-1"     |
| **StackId**      | ""              |
| **StackName**    | ""              |
| **URLSuffix**    | "amazonaws.com" |
_Note: Bold variables are not fully impletmented yet see the [Roadmap](#roadmap)_

A real unit testing example using Pytest can be seen [here](./tests/functional/test_template.py)

</details>

<details>
<summary>Function Testing</summary>
Using Cloud-Radar starts by importing it into your test file or framework.

```python
from cloud_radar import Test

# Test is a context manager that makes sure your stacks are deleted after testing.

# test-name is the name of your test from your taskcat project file.
# ./project_dir is the path to the folder that contains your Cloudformation template
# and taskcat config file.
with Test('test-name', './project_dir') as stacks:
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

# Once the test is over then all resources will be cleaned up.
```

You can also supply a Taskcat config as a python dictionary.

```python
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

with Test('log-bucket', './project_dir', config_input=config) as stacks:
    for stack in stacks:
      assert 'us-east' not in stack.region.name
```

You can also skip the context manager. Here is an example for `unittest`

```python
import unittest

from cloud-radar import TestManager

class Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tm = TestManager('test-name','./project_dir')
        cls.tm.create()

    @classmethod
    def tearDownClass(cls):
        cls.tm.delete()

    def test_bucket(self):
        stacks = self.__class__.tm.stacks

        for stack in stacks:
            # Test
```

Calling `help(cloud-radar.Test)`

```
Test(test_name: str, project_dir: str, config_input: dict = None, config_file: str = './.taskcat.yml', regions: str = 'ALL', wait_for_delete: bool = False) -> Iterator[taskcat._cfn.stack.Stacks]
    Create Stacks for a Taskcat test and return the stacks.

    Must pass in a Taskcat configuration as either a dictionary or file.

    Args:
        test_name (str): The name of the test from the Taskcat config file.
        project_dir (str): The directory that contains your Taskcat config and cloudformation files.
        config_input (dict, optional): Taskcat config file in the form of a dictionary. Defaults to None.
        config_file (str, optional): The name of the Taskcat config file. Defaults to "./.taskcat.yml".
        regions (str, optional): Overide the regions defined in the config file. Defaults to "ALL".
        wait_for_delete (bool, optional): Wait until stacks have deleted. Defaults to False.

    Yields:
        Iterator[Stacks]: The stacks created for the tests.
```

All the properties and methods of a [stack instance](https://github.com/aws-quickstart/taskcat/blob/main/taskcat/_cfn/stack.py#L188).

A real functional testing example using Pytest can be seen [here](./tests/functional/test_e2e.py)

</details>

## Roadmap

### Project
- Python 3.7 support
- Add Logging
- Add Logo
- Make it easier to interact with stack resources.
  * Getting a resource for testing should be as easy as `stack.Resources('MyResource)` or `template.Resources('MyResource')`

### Unit
- Implement all AWS [intrinsic functions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html).
  * Only `!Ref`, `!Sub`, `!Equals` and `!If` currently supported.
- Add full functionality to pseudo variables.
  * Variables like `Partition`, `URLSuffix` should change if the region changes.
  * Variables like `StackName` and `StackId` should have a better default than ""
- Handle References to resources that shouldn't exist.
  * It's currently possible that a `!Ref` to a Resource stays in the final template even if that resource is later removed because of a conditional.

### Functional
- Add the ability to update a stack instance to Taskcat.
- Add logging to Cloud-Radar
- Add logo

See the [open issues](https://github.com/DontShaveTheYak/cloud-radar/issues) for a list of proposed features (and known issues).

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

This project uses poetry to manage dependencies and pre-commit to run formatting, linting and tests. You will need to have both installed to your system as well as python 3.9.

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

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[python-shield]: https://img.shields.io/pypi/pyversions/cloud-radar?style=for-the-badge
[version-shield]: https://img.shields.io/pypi/v/cloud-radar?label=latest&style=for-the-badge
[pypi-url]: https://pypi.org/project/cloud-radar/
[test-shield]: https://img.shields.io/github/workflow/status/DontShaveTheYak/cloud-radar/Tests?label=Tests&style=for-the-badge
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
