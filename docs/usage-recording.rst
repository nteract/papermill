Record
======

**DEPRECATED** This functionality will be removed entirely in papermill 1.0.
See scrapbook's `glue <https://nteract-scrapbook.readthedocs.io/en/latest/usage-glue.html>`_.

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


Recover recorded values
-----------------------

Users can recover those values as a Pandas dataframe via the
``read_notebook`` function.

.. code-block:: python

   """summary.ipynb"""
   import papermill as pm

   nb = pm.read_notebook('notebook.ipynb')
   nb.dataframe

.. image:: img/nb_dataframe.png
