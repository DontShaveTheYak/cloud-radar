
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


# Advanced Naming Convention Checks

With the previous examples you can easily target individual resources to check their names meet expectations, but adding a test like this for every single resource in templates across your organisation is monotonous and time consuming. It is common for organisations to define conventions like all S3 buckets should have a naming convention like `{company name}-{AWS region}-{some name}`. This example covers the more advanced case for doing resource type to pattern conventions. This example is taken from the `test_naming_conventions` method of [test_naming_advanced.py](./test_naming_advanced.py).


```python
    # Ideally this dict would be coming from a common library
    # function that you have shared between all your test cases
    # (assuming consistency is the goal).
    #
    # This defines all the resource types we want to check, the pattern to match,
    # and either the details of the Tag or Property that the name is held in.
    type_patterns = {
        "AWS::EFS::FileSystem": {
            "Tag": "Name",
            # This TagProperty is optional. The default is 'Tags',
            # but some resources use a different property name for
            # their tags.
            "TagProperty": "FileSystemTags",
            "Pattern": r"^[a-z0-9-]*-vol$",
        },
        "AWS::S3::Bucket": {
            "Property": "BucketName",
            "Pattern": r"^[a-z0-9-]*-xx-west-3[a-z0-9-]*$",
        },
        "AWS::S3::BucketPolicy": {
            # The BucketPolicy type does not support custom names. If we do not
            # want to set fail_on_missing_type=False when we call the assertion
            # below then we need to include this type in the dict, and set it
            # not to be checked.
            # This approach ensures that types do not slip through unintentionally.
            "Check": False
        },
    }

    stack.assert_resource_type_property_value_conventions(type_patterns)
```

In this example our object containing our naming conventions includes three types, showing the different types of configuration that can be used:

1. `AWS::EFS::FileSystem` - A resource type which holds it's name in the tag `Name`, using a non-standard tag property `FileSystemTags`
2. `AWS::S3::Bucket` - A resource type which holds it's name in a property called `BucketName`
3. `AWS::S3::BucketPolicy` - A resource type which does not have a custom name, so is configured not to perform any pattern checking. This is required to be configured unless `fail_on_missing_type=False` is supplied to the `assert_resource_type_property_value_conventions` method.


If a resource is encountered that did not match the defined pattern, you would get a test failure with an error like this:
```
E       AssertionError: Resource 'rFileSystem' tag 'Name' value 'my-test-xx-west-3-vol' did not match expected pattern '^[a-z0-9-]*-FAIL$'.
```

The default behaviour is for `fail_on_missing_type` to be True, so if a resource is encountered with a type not defined in `type_patterns`, an assertion error like the following will be raised.
```
E           AssertionError: Resource 'rFileSystem' has type 'AWS::EFS::FileSystem' which is not included in the supplied type_patterns.
```
