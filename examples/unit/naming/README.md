
 # What does this example cover?

 This example shows two main scenarios:
 * That resources are named as expected, including after various parameters have been substituted in using functions like `!Sub`.
 * That resources are named following defined conventions defined by regex patterns, including after various parameters have been substituted in using functions like `!Sub`.

This is complicated by the fact that different CloudFormation resources have their name stored in different properties. Sometimes it is in top level Property field, sometimes it is in a Tag, and not all resources support a custom name being assigned. The complete list of resources which support a custom name is detailed in [this AWS documentation page](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-name.html).

# Static name examples

We can check that a resource in a stack exactly matches expectation using one of the following two approaches, depending on if it is a property or a tag. This example is taken from the `test_static_naming` method of [test_naming_simple.py](./test_naming_simple.py).

```python
    # Get the bucket & check it has the expected name, based on a property
    bucket = stack.get_resource("rS3Bucket")
    bucket.assert_property_has_value("BucketName", "test-xx-west-3-bucket")

    # The EFS volume in this template also has a name including substitutions,
    # but this time the value is in a tag.
    # This resource type uses a non-standard Tag property
    efs_vol = stack.get_resource("rFileSystem")
    efs_vol.assert_tag_has_value("Name", "my-test-xx-west-3-vol", "FileSystemTags")
```

If a resource was incorrectly named, this would cause an assertion error to be raised like this:
```
E       AssertionError: Resource 'rS3Bucket' property 'BucketName' value 'tet-xx-west-3-bucket' did not match input value 'test-xx-west-3-bucket'.
```


# Pattern name examples

We can check that a resource in a stack matches a regex pattern using one of the following two approaches, depending on if it is a property or a tag. This example is taken from the `test_naming_pattern` method of [test_naming_simple.py](./test_naming_simple.py).

```python
    # Get the bucket & check it contains the region name somewhere in
    # it (a pretty common naming convention).
    bucket = stack.get_resource("rS3Bucket")
    bucket.assert_property_value_matches_pattern("BucketName", r"^[a-z0-9-]*-xx-west-3[a-z0-9-]*$")

    # The EFS volume in this template also has a name including substitutions,
    # but this time the value is in a tag.
    # For a pattern to match we will just check that is ends in "-vol".
    efs_vol = stack.get_resource("rFileSystem")
    # This last attribute is optional, and defaults to Tags which is used in many
    # resources.
    efs_vol.assert_tag_value_matches_pattern("Name", r"^[a-z0-9-]*-vol$", "FileSystemTags")

```

If a resource was incorrectly named and did not match the expected pattern, this would cause an assertion error to be raised like this:

```
E       AssertionError: Resource 'rFileSystem' tag 'Name' value 'my-test-xx-west-3-vol' did not match expected pattern '^[a-z]*-vol$'.
```


# Advanced Naming Convention Checks

With the previous examples you can easily target individual resources to check their names meet expectations, but adding a test like this for every single resource in templates across your organisation is monotonous and time consuming. It is common for organisations to define conventions like all S3 buckets should have a naming convention like "{company name}-{AWS region}-{some name}". This example covers the more advanced case for doing resource type to pattern conventions. This example is taken from the `XXX` method of [test_naming_advanced.py](./test_naming_advanced.py).



If a resource was encountered that did not match the defined convention, you would get a test failure with an error like this:

```
E           AssertionError: Name does not match convention regex
E           assert None
E            +  where None = <function match at 0x104637010>('^-queu$', 'my-queue')
E            +    where <function match at 0x104637010> = re.match
```

If YYY is set to True (the default value) and a resource is encountered with a type not defined in ZZZ, an assertion error will be raised.
```
E           AssertionError: Resource 'rFileSystem' has type 'AWS::EFS::FileSystem' which is not included in the supplied type_patterns.
```

As noted in the introduction however, not all resources support custom names. To work around this, and avoid this library attempting to maintain a list of resources that support names or not, a type entry can be defined in the `type_patterns` dict like this:

```python
{
    "AWS::S3::BucketPolicy": {
        "Check": False
    }
}
```


When writing this type of test I will commonly set the region that Cloud Radar is using to once that does not exist in realitiy, or certainly is not one that we use - this helps catch where a region may be hard coded which may lead to incorrect naming when the stack is deployed to a different region.

The basic premise is we hold a map keyed on the resource type and the value being a dict holding the path to the name and the regex that the name is expected to match. Then we can iterate through each resource in the resolved template checking values.

TODO HOW
