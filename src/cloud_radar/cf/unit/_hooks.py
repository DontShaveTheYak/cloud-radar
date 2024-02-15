from dataclasses import dataclass

# Work around some circular import issue until someone smarter
# can work out the right way to restructure / refactor this
# Solution from https://stackoverflow.com/a/39757388/230449
from typing import TYPE_CHECKING, Callable, Dict, List, Union

from ._resource import Resource
from ._stack import Stack

if TYPE_CHECKING:
    from ._template import Template


@dataclass
class ResourceHookContext:
    """Class that contains the context for a resource hook to evaluate.

    Attributes:
        logical_id (str): The logical ID for the resource in the CloudFormation
            template which is to be evaluated.
        resource_definition (Resource): The definition of the resource to be evaluated.
        stack (Stack): the rendered stack that the resource is part of
        template (Template): the template that is being rendered to produce the stack
    """

    logical_id: str
    resource_definition: Resource
    stack: Stack
    template: "Template"


@dataclass
class ResourceHookCollection:
    """
    Class that holds the two collections of hooks that we can evaluate against
    individual Resource items in a rendered stack.

    Each Callable is expected to take in a single parameter - an instance of
    ResourceHookContext.

    Attributes:
        plugin (Dict[str, List[Callable]]): The dict of Resource Type to
            list of hooks which were loaded from plugins.
        local (Dict[str, List[Callable]]): The dict of Resource Type to
            list of hooks which were defined with the template.
    """

    plugin: Dict[str, List[Callable]]
    local: Dict[str, List[Callable]]


@dataclass
class TemplateHookCollection:
    """
    Class that holds the two collections of hooks that we can evaluate
    against a loaded Template.

    Each Callable is expected to take in a single parameter - an
    instance of Template.

    Attributes:
        plugin (List[Callable]): The list of hooks which were loaded from plugins.
        local (List[Callable]): The list of hooks which were defined with the template.
    """

    plugin: List[Callable]
    local: List[Callable]


class HookProcessor:
    """
    Class that handles holding and evaluating the collections of hooks that we run
    against Templates and Resources.

    In future this will include loading hooks from plugins, but that has not been
    implemented yet.

    This supports suppressing rules based on Metadata at either the Template or
    Resource level, using something like this:

    Metadata:
      Cloud-Radar:
        ignore-hooks:
          - s3_check_bucket_name_region

    To allow this to work, you should ensure that the function names that you implement
    for hooks have unique and descriptive names.

    """

    def __init__(self) -> None:
        self._resources: ResourceHookCollection = ResourceHookCollection(
            plugin={}, local={}
        )
        self._template: TemplateHookCollection = TemplateHookCollection(
            plugin=[], local=[]
        )
        # TODO: Add support for loading plugin hooks

    @property
    def template(self):
        return self._template.local

    @template.setter
    def template(self, value: List[Callable]):
        self._template.local = value

    @property
    def resources(self):
        return self._resources.local

    @resources.setter
    def resources(self, value: Dict[str, List[Callable]]):
        self._resources.local = value

    def _is_hook_suppressed_in_dict(self, hook_name: str, metadata: Dict) -> bool:
        cloud_radar_metadata = metadata.get("Cloud-Radar", {})
        ignored_hooks = cloud_radar_metadata.get("ignore-hooks", {})

        return hook_name in ignored_hooks

    def _is_hook_suppressed(
        self, hook_name, template: "Template", resource: Union[Resource, None] = None
    ) -> bool:
        # First check if a suppression exists in the template,
        # as that will take precedence.
        hook_suppressed = self._is_hook_suppressed_in_dict(
            hook_name, template.template.get("Metadata", {})
        )

        if not hook_suppressed and resource:
            # if not suppression was found at the template level, check the
            # resource level
            hook_suppressed = self._is_hook_suppressed_in_dict(
                hook_name, resource.get("Metadata", {})
            )

        return hook_suppressed

    def _evaluate_template_hooks(
        self, hook_type: str, hooks: List[Callable], template: "Template"
    ) -> None:
        for single_hook in hooks:
            # Only process the hook if it has not been marked as to be
            # ignored
            if not self._is_hook_suppressed(single_hook.__name__, template, None):
                print(f"Processing {hook_type} hook {single_hook.__name__}")

                single_hook(template=template)

    def _evaluate_resource_hooks(
        self,
        hook_type: str,
        hooks: Dict[str, List[Callable]],
        stack: Stack,
        template: "Template",
    ) -> None:
        # Iterate through the resources in the rendered stack
        for logical_id in stack.data.get("Resources", {}):
            print("Got resource " + logical_id)
            resource_definition = stack.get_resource(logical_id)

            resource_type = resource_definition.get("Type")

            # Get the hooks that have been defined for this type of resource
            type_hooks = hooks.get(resource_type, [])

            hook_context = ResourceHookContext(
                logical_id=logical_id,
                resource_definition=resource_definition,
                stack=stack,
                template=template,
            )

            # Iterate through each defined hook and call them.
            for single_hook in type_hooks:
                # Only process the hook if it has not been marked as to be
                # ignored
                if not self._is_hook_suppressed(
                    single_hook.__name__, template, resource_definition
                ):
                    print(f"Processing {hook_type} hook {single_hook.__name__}")

                    single_hook(context=hook_context)

    def evaluate_resource_hooks(self, stack: Stack, template: "Template") -> None:
        # Evaluate the global hooks first, then the local ones
        self._evaluate_resource_hooks("plugin", self._resources.plugin, stack, template)
        self._evaluate_resource_hooks("local", self._resources.local, stack, template)

    def evaluate_template_hooks(self, template: "Template") -> None:
        print(template)
        # raise ValueError(type(template))
        # raise ValueError(template.template)

        # Evaluate the global hooks first, then the local ones
        self._evaluate_template_hooks("plugin", self._template.plugin, template)
        self._evaluate_template_hooks("local", self._template.local, template)
