 # -*- coding: utf-8 -*-
"""
Deduce parameters of a notebook from the parameters cell.
"""

from __future__ import unicode_literals, print_function

import ast
from collections import namedtuple


Parameter = namedtuple('Parameter', [
    'name',
    'inferred_type_name',  # string of type
    'default',  # string representing the default value
    'language',
])


def guess_parameters(node):
    """Guess parameter types in a notebook."""
    lang = node['metadata']['language_info']['name']
    if lang in _parameter_inspectors:
        return _parameter_inspectors[lang](node)
    return node


# Registry for functions that inspect parameters.
_parameter_inspectors = {}


def register_inspector(name):
    """Decorator for registering functions that inspect parameters.

    Wrapped functions should return a mapping of variable name to type name."""

    def wrapper(func):
        _parameter_inspectors[name] = func
        return func

    return wrapper


# Python inspector
@register_inspector('python')
def guess_python_parameters(node):
    params = []
    for cell in node.cells:
        if 'parameters' in cell.get('metadata', {}).get('tags', []):
            src = cell['source']
            for node in ast.parse(src).body:
                if not isinstance(node, ast.Assign):
                    continue
                if not len(node.targets) == 1:
                    continue
                value = ast.literal_eval(node.value)
                value_type = type(value)
                type_name = None if value_type is type(None) else value_type.__name__
                params.append(Parameter(
                    name=node.targets[0].id,
                    inferred_type_name=type_name,
                    default=repr(ast.literal_eval(node.value)),
                    language='python',
                ))
    return params
