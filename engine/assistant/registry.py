"""Closed workflow registry. Add a definition/adapter; the chat UI remains generic."""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class WorkflowDefinition:
    id: str
    label: str
    description: str
    compile: Callable
    prepare: Callable


_workflows = {}


def register(definition):
    if definition.id in _workflows:
        raise ValueError("Duplicate assistant workflow: " + definition.id)
    _workflows[definition.id] = definition


def workflows():
    from . import workflows as adapters  # noqa: F401
    return tuple(_workflows.values())


def get(workflow_id):
    workflows()
    if workflow_id not in _workflows:
        raise ValueError("Välj ett registrerat arbetsflöde.")
    return _workflows[workflow_id]


def catalog():
    return [{"id": item.id, "label": item.label, "description": item.description} for item in workflows()]
