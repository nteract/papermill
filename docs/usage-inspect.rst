Inspect
=======

The two ways to inspect the notebook to discover its parameters are: (1) through the
Python API and (2) through the command line interface.

Execute via the Python API
~~~~~~~~~~~~~~~~~~~~~~~~~~

The `inspect_notebook` function can be called to inspect a notebook:

.. code-block:: python

   inspect_notebook(<notebook path>)



.. code-block:: python

   import papermill as pm

   pm.inspect_notebook('path/to/input.ipynb')

.. note::
    If your path is parametrized, you can pass those parameters in a dictionary
    as second parameter:

    ``inspect_notebook('path/to/input_{month}.ipynb', parameters={month='Feb'})``

Inspect via CLI
~~~~~~~~~~~~~~~

To inspect a notebook using the CLI, enter the ``papermill --help-notebook`` command in the
terminal with the notebook and optionally path parameters.

.. seealso::

    :doc:`CLI reference <./usage-cli>`

Inspect a notebook
^^^^^^^^^^^^^^^^^^

Here's an example of a local notebook being inspected and an output example:

.. code-block:: bash

    papermill --help-notebook ./papermill/tests/notebooks/complex_parameters.ipynb

    Usage: papermill [OPTIONS] NOTEBOOK_PATH [OUTPUT_PATH]

    Parameters inferred for notebook './papermill/tests/notebooks/complex_parameters.ipynb':
    msg: Unknown type (default None)
    a: float (default 2.25)         Variable a
    b: List[str] (default ['Hello','World'])
                                    Nice list
    c: NoneType (default None)
