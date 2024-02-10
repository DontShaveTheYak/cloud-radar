from dataclasses import dataclass

# Work around some circular import issue until someone smarter
# can work out the right way to restructure / refactor this
# Solution from https://stackoverflow.com/a/39757388/230449
from typing import TYPE_CHECKING, Callable, Dict, List

from ._resource import Resource
from ._stack import Stack

if TYPE_CHECKING:
    from ._template import Template


@dataclass
class ResourceHookContext:
    logical_id: str
    resource_definition: Resource
    stack: Stack
    template: "Template"


@dataclass
class ResourceHookCollection:
    plugin: Dict[str, List[Callable]]
    local: Dict[str, List[Callable]]


@dataclass
class TemplateHookCollection:
    plugin: List[Callable]
    local: List[Callable]


class Hooks:
    """
    Might as well move the complexity of hooks into a separate file instead of
    cluttering template up more!

    Especially once this also need to handle plugins!

    TODO: Proper docs
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

    def _evaluate_template_hooks(
        self, hook_type: str, hooks: List[Callable], template: "Template"
    ) -> None:
        for single_hook in hooks:
            print(f"Processing {hook_type} hook {single_hook.__name__}")

            # TODO: Check if template has metadata to skip hook,
            # looking for skip.<function name>
            single_hook(template=template)

    def _evaluate_all_template_hooks(self, template: "Template") -> None:
        # Use cases:
        # - Ensuring all templates have some common parameters, e.g. Environment,  Lifecycle
        # - Ensuring logical id naming conventions of
        #   Parameters starting with "p" etc are followed

        # Evaluate the global hooks first, then the local ones
        self._evaluate_template_hooks("plugin", self._template.plugin, template)
        self._evaluate_template_hooks("local", self._template.local, template)

    def _evaluate_resource_hooks(
        self,
        hook_type: str,
        hooks: Dict[str, List[Callable]],
        stack: Stack,
        template: "Template",
    ) -> None:
        for logical_id in stack.data.get("Resources", {}):
            print("Got resource " + logical_id)
            resource_definition = stack.get_resource(logical_id)

            resource_type = resource_definition.get("Type")

            type_hooks = hooks.get(resource_type, [])

            hook_context = ResourceHookContext(
                logical_id=logical_id,
                resource_definition=resource_definition,
                stack=stack,
                template=template,
            )

            for single_hook in type_hooks:
                print(f"Processing {hook_type} hook {single_hook.__name__}")

                # TODO: Check if resource has metadata to skip hook,
                # looking for skip.<function name>
                single_hook(context=hook_context)

    def _evaluate_all_resource_hooks(self, stack: Stack, template: "Template") -> None:
        # Evaluate the global hooks first, then the local ones
        self._evaluate_resource_hooks("plugin", self._resources.plugin, stack, template)
        self._evaluate_resource_hooks("local", self._resources.local, stack, template)

    def evaluate_hooks(self, stack: Stack, template: "Template") -> None:
        self._evaluate_all_resource_hooks(stack, template)
        print("TODO: Evaluate all hooks")
