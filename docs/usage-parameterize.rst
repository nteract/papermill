Parameterize
============

.. seealso::

    :doc:`Workflow reference <./reference/papermill-workflow>`



Generally, the first workflow step when using papermill is to parameterize the notebook.

To do this, you will tag notebook cells with ``parameters``. These
``parameters`` are later used when the notebook is executed or run.

Designate parameters for a cell
-------------------------------

To parameterize your notebook, designate a cell with the tag ``parameters``.


.. image:: img/parameters.png


If you are using the `Jupyter Notebook`_ interface, you must activate the tagging toolbar 
by navigating to ``View``, ``Cell Toolbar``, and then ``Tags``.

If you are using the `JupyterLab`_ interface, after selecting the cell you want to
parameterize, click the cell inspector (wrench icon). Now you should edit the
``Cell Metadata`` field by adding ``"tags":["parameters"]``. Learn more about the
jupyter notebook format and metadata fields `here`_. You can also consider using
an extension such as `jupyterlab-celltags`_.

How do parameters work
----------------------

Papermill looks for the ``parameters`` cell and treats those values as defaults
for the parameters passed in at execution time. It achieves this by inserting a
cell after the tagged cell. If no cell is tagged with ``parameters`` a cell will
be inserted to the front of the notebook.


.. _`JupyterLab`: https://github.com/jupyterlab/jupyterlab
.. _`Jupyter Notebook`: https://github.com/jupyter/notebook
.. _`here`: https://ipython.org/ipython-doc/dev/notebook/nbformat.html#cell-metadata
.. _`jupyterlab-celltags`: https://github.com/jupyterlab/jupyterlab-celltags