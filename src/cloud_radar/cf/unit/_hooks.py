from ._stack import Stack

# from ._template import Template


class Hooks:
    """
    Might as well move the complexity of hooks into a separate file instead of cluttering template up more!

    Especially once this also need to handle plugins!

    TODO: Proper docs
    """

    def __init__(self) -> None:
        self._resources = {"global": {}, "local": {}}  # TODO: Load!

    @property
    def resources(self):
        return self._resources["local"]

    @resources.setter
    def resources(self, value: dict):
        self._resources["local"] = value

    def _evaluate_resource_hooks(self, stack: Stack, template: dict) -> None:
        # Evaluate the global hooks first, then the local ones
        for hook_type in ("global", "local"):
            for resource_name in stack.data.get("Resources", {}):
                print("Got resource " + resource_name)
                resource_value = stack.get_resource(resource_name)

                resource_type = resource_value.get("Type")

                type_hooks = self._resources[hook_type].get(resource_type, [])

                for single_hook in type_hooks:
                    print("Got hook " + single_hook.__name__)

                    # TODO: Check if resource has metadata to skip hook, looking for skip.<function name>
                    single_hook(
                        resource_data=resource_value,
                        stack_info=stack,
                        template_info=template,
                    )

    def evaluate_hooks(self, stack: Stack, template: dict) -> None:
        self._evaluate_resource_hooks(stack, template)
        print("TODO: Evaluate all hooks")
