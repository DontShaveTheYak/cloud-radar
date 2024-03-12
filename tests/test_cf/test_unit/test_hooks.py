from cloud_radar.cf.unit._hooks import HookProcessor

# Test the pieces of _hooks.py that can be tested independently in a unit test.
# Most of the testing of this functionality is covered through the
# examples/unit/hooks tests.


# Tests that when multiple plugins are loaded their results are combined.
# This contains an assortment of fake plugins that implement one or both
# of the methods to provide hooks.
def test_load_hooks_from_single_plugin():
    # Define the plugins
    plugin_one = {
        "get_template_hooks": get_template_hooks_one,
        "get_resource_hooks": get_resource_hooks_one,
    }
    plugin_two = {"get_template_hooks": get_template_hooks_two}
    plugin_three = {"get_resource_hooks": get_resource_hooks_two}

    # Create the hook processor and load each plugin, performing assertions along the way
    hooks = HookProcessor()
    hooks._load_hooks_from_single_plugin(plugin_one)

    assert len(hooks._template.plugin) == 1
    # raise ValueError(type(hooks._template.plugin[0][0]))
    assert template_hook_one in hooks._template.plugin

    assert len(hooks._resources.plugin.get("AWS::S3::Bucket")) == 1
    assert s3_hook_one in hooks._resources.plugin.get("AWS::S3::Bucket")

    assert len(hooks._resources.plugin.get("AWS::SES::ReceiptRule")) == 1
    assert ses_hook_one in hooks._resources.plugin.get("AWS::SES::ReceiptRule")

    hooks._load_hooks_from_single_plugin(plugin_two)
    assert len(hooks._template.plugin) == 2
    assert template_hook_one in hooks._template.plugin
    assert template_hook_two in hooks._template.plugin

    hooks._load_hooks_from_single_plugin(plugin_three)
    assert len(hooks._template.plugin) == 2
    assert len(hooks._resources.plugin.get("AWS::S3::Bucket")) == 2
    assert s3_hook_one in hooks._resources.plugin.get("AWS::S3::Bucket")
    assert s3_hook_two in hooks._resources.plugin.get("AWS::S3::Bucket")
    assert len(hooks._resources.plugin.get("AWS::SES::ReceiptRule")) == 1
    assert ses_hook_one in hooks._resources.plugin.get("AWS::SES::ReceiptRule")


# Below here is functions to allow the test to work
def get_template_hooks_one():
    return [template_hook_one]


def get_template_hooks_two():
    return [template_hook_two]


def get_resource_hooks_one():
    return {"AWS::S3::Bucket": [s3_hook_one], "AWS::SES::ReceiptRule": [ses_hook_one]}


def get_resource_hooks_two():
    return {"AWS::S3::Bucket": [s3_hook_two]}


def template_hook_one():
    print("template_hook_one")


def template_hook_two():
    print("template_hook_two")


def s3_hook_one():
    print("s3_hook_one")


def s3_hook_two():
    print("s3_hook_two")


def ses_hook_one():
    print("ses_hook_one")
