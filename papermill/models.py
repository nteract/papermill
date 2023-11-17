"""Models used by papermill."""
from collections import namedtuple

Parameter = namedtuple(
    'Parameter',
    [
        'name',
        'inferred_type_name',  # string of type
        'default',  # string representing the default value
        'help',
    ],
)
