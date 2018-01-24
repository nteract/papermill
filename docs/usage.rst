Usage
=====

Parameterizing a Notebook
-------------------------

To parameterize your notebook designate a cell with the tag ``parameters``.
Papermill looks for the ``parameters`` cell and treat those values as defaults
for the parameters passed in at execution time. It achieves this by inserting a
cell after the tagged cell. If no cell is tagged with ``parameters`` a cell will
be inserted to the front of the notebook.

.. image:: img/parameters.png

Executing a Notebook
--------------------

The two ways to execute the notebook with parameters are: (1) through the
Python API and (2) through the command line interface.

Execute via the Python API
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import papermill as pm

   pm.execute_notebook(
      'path/to/input.ipynb',
      'path/to/output.ipynb',
      parameters = dict(alpha=0.6, ratio=0.1)
   )

Execute via CLI
~~~~~~~~~~~~~~~

Here's an example of a local notebook being executed and output to an
Amazon S3 account:

.. code-block:: bash

   $ papermill local/input.ipynb s3://bkt/output.ipynb -p alpha 0.6 -p l1_ratio 0.1

Recording Values to the Notebook
--------------------------------

Users can save values to the notebook document to be consumed by other
notebooks.

Recording values to be saved with the notebook.

.. code-block:: python

   """notebook.ipynb"""
   import papermill as pm

   pm.record("hello", "world")
   pm.record("number", 123)
   pm.record("some_list", [1, 3, 5])
   pm.record("some_dict", {"a": 1, "b": 2})

Users can recover those values as a Pandas dataframe via the
``read_notebook`` function.

.. code-block:: python

   """summary.ipynb"""
   import papermill as pm

   nb = pm.read_notebook('notebook.ipynb')
   nb.dataframe

.. image:: img/nb_dataframe.png

Displaying Plots and Images Saved by Other Notebooks
----------------------------------------------------

Display a matplotlib histogram with the key name ``matplotlib_hist``.

.. code-block:: python

   """notebook.ipynb"""
   import papermill as pm
   from ggplot import mpg
   import matplotlib.pyplot as plt

   # turn off interactive plotting to avoid double plotting
   plt.ioff()

   f = plt.figure()
   plt.hist('cty', bins=12, data=mpg)
   pm.display('matplotlib_hist', f)

.. image:: img/matplotlib_hist.png

Read in that above notebook and display the plot saved at ``matplotlib_hist``.

.. code-block:: python

   """summary.ipynb"""
   import papermill as pm

   nb = pm.read_notebook('notebook.ipynb')
   nb.display_output('matplotlib_hist')

.. image:: img/matplotlib_hist.png

Analyzing a Collection of Notebooks
-----------------------------------

Papermill can read in a directory of notebooks and provides the
``NotebookCollection`` interface for operating on them.

.. code-block:: python

   """summary.ipynb"""
   import papermill as pm

   nbs = pm.read_notebooks('/path/to/results/')

   # Show named plot from 'notebook1.ipynb'
   # Accepts a key or list of keys to plot in order.
   nbs.display_output('train_1.ipynb', 'matplotlib_hist')

.. image:: img/matplotlib_hist.png

.. code-block:: python

   # Dataframe for all notebooks in collection
   nbs.dataframe.head(10)

.. image:: img/nbs_dataframe.png