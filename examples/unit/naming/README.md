
 # What does this example cover?

 This example shows two main scenarios, both relating to the state of the template after various parameters have been substituted in using functions like `!Sub`:
 * That resources are named as expected exactly
 * That resources are named following conventions defined by regex patterns

This is complicated by the fact that different CloudFormation resources have their name stored in different properties. Sometimes it is in top level Property field, sometimes it is in a Tag, and not all resources support a custom name being assigned. The complete list of resources which support a custom name is detailed in [this AWS documentation page](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-name.html).

This library does not aim to keep a record internally of what types support custom names or where that information may be stored.

When writing this type of test I will commonly set the region that Cloud Radar is using to one that does not exist in reality, or certainly is not one that we use - this helps catch where a region may be hard coded in a template leading to incorrect naming when the stack is deployed to a different region. The region used when the stack is rendered can be set like this:

```python
return template.create_stack(params={"pName": "test"}, region="xx-west-3")
```

# Static name examples

We can check that the name of a resource in a stack exactly matches expectations using one of the following two approaches, depending on if it is a property or a tag. This example is taken from the `test_static_naming` method of [test_naming_simple.py](./test_naming_simple.py).

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

We can check that the name of a resource in a stack matches a regex pattern using one of the following two approaches, depending on if it is a property or a tag. This example is taken from the `test_naming_pattern` method of [test_naming_simple.py](./test_naming_simple.py).

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
