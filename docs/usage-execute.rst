Execute
=======

The two ways to execute the notebook with parameters are: (1) through the
Python API and (2) through the command line interface.

Execute via the Python API
~~~~~~~~~~~~~~~~~~~~~~~~~~

The `execute_notebook` function can be called to execute an input notebook
when passed a dictionary of parameters:

.. code-block:: python

   execute_notebook(<input notebook>, <output notebook>, <dictionary of parameters>)



.. code-block:: python

   import papermill as pm

   pm.execute_notebook(
      'path/to/input.ipynb',
      'path/to/output.ipynb',
      parameters=dict(alpha=0.6, ratio=0.1)
   )

Execute via CLI
~~~~~~~~~~~~~~~

To execute a notebook using the CLI, enter the ``papermill`` command in the
terminal with the input notebook, location for output notebook, and options.

.. seealso::

    :doc:`CLI reference <./usage-cli>`

Execute a notebook with parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's an example of a local notebook being executed and output to an
Amazon S3 account:

.. code-block:: bash

   $ papermill local/input.ipynb s3://bkt/output.ipynb -p alpha 0.6 -p l1_ratio 0.1

In the above example, two parameters are set: ``alpha`` and ``l1_ratio`` using ``-p`` (``--parameters`` also works).
Parameter values that look like booleans or numbers will be interpreted as such.

Here are the different ways users may set parameters:

Using raw strings as parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using ``-r`` or ``--parameters_raw``, users can set parameters one by one. However, unlike ``-p``, the parameter will
remain a string, even if it may be interpreted as a number or boolean.

.. code-block:: bash

    $ papermill local/input.ipynb s3://bkt/output.ipynb -r version 1.0

Using a parameters file
^^^^^^^^^^^^^^^^^^^^^^^

Using ``-f`` or ``--parameters_file``, users can provide a YAML file from which parameter values should be read.

.. code-block:: bash

    $ papermill local/input.ipynb s3://bkt/output.ipynb -f parameters.yaml

Using a YAML string for parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using ``-y`` or ``--parameters_yaml``, users can directly provide a YAML string containing parameter values.

.. code-block:: bash

    $ papermill local/input.ipynb s3://bkt/output.ipynb -y "
    x:
        - 0.0
        - 1.0
        - 2.0
        - 3.0
    linear_function:
        slope: 3.0
        intercept: 1.0"

Using ``-b`` or ``--parameters_base64``, users can provide a YAML string, base64-encoded, containing parameter values.

.. code-block:: bash

    $ papermill local/input.ipynb s3://bkt/output.ipynb -b YWxwaGE6IDAuNgpsMV9yYXRpbzogMC4xCg==

Note about using YAML
^^^^^^^^^^^^^^^^^^^^^

When using YAML to pass arguments, through ``-y``, ``-b`` or ``-f``, parameter values can be arrays or dictionaries:

.. code-block:: bash

    $ papermill local/input.ipynb s3://bkt/output.ipynb -y "
    x:
        - 0.0
        - 1.0
        - 2.0
        - 3.0
    linear_function:
        slope: 3.0
        intercept: 1.0"

Note about using with multiple account credentials
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use multiple AWS accounts and are accessing S3 files, you can
`configure your AWS credentials <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html>`__,
to specify which account to use by setting the `AWS_PROFILE` environment
variable at the command-line. For example:

.. code-block:: bash

    $ AWS_PROFILE=dev_account papermill local/input.ipynb s3://bkt/output.ipynb -p alpha 0.6 -p l1_ratio 0.1

A similar pattern may be needed for other types of remote storage accounts.

Tracking the Execution with Cell Descriptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you want to keep track of the execution in a closer way, you can add cell descriptions to the notebook being executed that will be injected to the TQDM progress bar.

Here is an example of the TQDM output during the execution of a 4-cells notebook without cell descriptions:

.. code-block:: bash

    10:10 # papermill input_notebook.ipynb output_notebook.ipynb
    Input Notebook:  input_notebook.ipynb
    Output Notebook: output_notebook.ipynb
    Executing:   0%|                                                                    | 0/4 [00:00<?, ?cell/s]Executing
    Executing:  25%|█████████                                                           | 1/4 [00:00<?, ?cell/s]Executing
    [...]

You can inject cell descriptions by adding a comment with the following formatting at the very beginning of each cell you are interested in:

.. code-block:: bash

    #papermill_description=TQDM_DESCRIPTION

In this way, when the execution will reach the cell tagged with the description, the TQDM progress bar will show the string TQDM_DESCRIPTION. Please be careful: the comment must not contain any space, otherwise it will be ignored.

Taking back our previous example, if we add the description 'FirstCell' to cell 0 and the description 'SecondCell' to the cell 1 we will get the TQDM to display the following information:

.. code-block:: bash

    10:12 # papermill input_notebook.ipynb output_notebook.ipynb
    Input Notebook:  input_notebook.ipynb
    Output Notebook: output_notebook.ipynb
    Executing FirstCell:   0%|                                                          | 0/4 [00:00<?, ?cell/s]Executing
    Executing SecondCell:  25%|█████████                                                 | 1/4 [00:00<?, ?cell/s]Executing
    [...]
