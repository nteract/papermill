Parameterize
============

.. seealso::

    :doc:`Workflow reference <./reference/papermill-workflow>`

Generally, the first workflow step when using papermill is to parameterize the
notebook.

To do this, tag notebook cells with ``parameters``. These ``parameters`` are
later used when the notebook is executed or run.

Designate parameters for a cell
-------------------------------

To parameterize a notebook, designate a cell with the tag ``parameters``.

.. image:: img/parameters.png

Notebook
~~~~~~~~

If using the `Jupyter Notebook`_ interface

1. Activate the tagging toolbar by navigating to ``View``, ``Cell Toolbar``, and then ``Tags``
2. Enter ``parameters`` into a textbox at the top right of a cell
3. Click ``Add tag``

Lab
~~~

If using the `JupyterLab`_ interface

1. Select the cell to parameterize
2. Click the cell inspector (wrench icon)
3. Edit the ``Cell Metadata`` field by adding ``"tags":["parameters"]``

Learn more about the jupyter notebook format and metadata fields `here`_.
For easier management, consider using an extension such as
`jupyterlab-celltags`_.

How parameters work
-------------------

``parameters`` cells are assumed to specify default values which may be
overridden by values specified at execution time.

If papermill finds a ``parameters`` tagged cell, a new cell is inserted
immediately after the tagged cell. If no cell is tagged ``parameters``, a cell
will be inserted at the top of the notebook.
Papermill's inserted cell contains only the overridden parameters.

One caveat is that a ``parameters`` cell may not behave intuitively with
inter-dependent parameters. Consider a notebook ``note.ipynb`` with two cells:

.. code-block:: python

  #parameters
  a = 1
  twice = a * 2

.. code-block:: python

  print("a =", a, "and twice =", twice)

when executed with ``papermill note.ipynb -p a 9``, the output will be
``a = 9 and twice = 2`` (not ``twice = 18``).

.. _`JupyterLab`: https://github.com/jupyterlab/jupyterlab
.. _`Jupyter Notebook`: https://github.com/jupyter/notebook
.. _`here`: https://ipython.org/ipython-doc/dev/notebook/nbformat.html#cell-metadata
.. _`jupyterlab-celltags`: https://github.com/jupyterlab/jupyterlab-celltags
