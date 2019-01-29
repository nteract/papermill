Parameterize
============

.. seealso::

    :doc:`API reference <./reference/papermill-api>`

    :doc:`Workflow reference <./reference/papermill-workflow>`



Generally, the first workflow step when using papermill is to parameterize the notebook.

To do this, you will tag notebook cells with ``parameters``. These
``parameters`` are later used when the notebook is executed or run.

Designate parameters for a cell
-------------------------------

To parameterize your notebook, designate a cell with the tag ``parameters``.


.. image:: img/parameters.png

How do parameters work
----------------------

Papermill looks for the ``parameters`` cell and treats those values as defaults
for the parameters passed in at execution time. It achieves this by inserting a
cell after the tagged cell. If no cell is tagged with ``parameters`` a cell will
be inserted to the front of the notebook.
