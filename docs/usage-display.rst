Display
=======

**DEPRECATED** This functionality will be removed entirely in papermill 1.0.
See scrapbook's `Notebook <https://nteract-scrapbook.readthedocs.io/en/latest/models.html#notebook>`_.

papermill offers flexibility to display content, such
as plots and images, which is found in other notebooks.

.. seealso::

    :ref:`display <display>`

    ``papermill.api.Notebook.display_output`` in :doc:`API reference <./reference/papermill-api>`


Displaying Content from Another Notebook
----------------------------------------

Let's look at an example with two notebooks, ``notebook.ipynb`` and
``summary.ipynb``.

Save content in one notebook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this example, let's create the ``notebook.ipynb`` which will
:ref:`display <display>` a matplotlib histogram (object f) with
the key name ``matplotlib_hist``.

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

Use content in a second notebook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now, let's work in a new notebook ``summary.ipynb``. We would like to use
the figure which we saved and displayed in the first notebook ``notebook.ipynb``.

To do so, use ``read_notebook`` to read in the above notebook. Use
papermill's ``display_output`` to display the plot saved with the
keyword ``matplotlib_hist``.

.. code-block:: python

   """summary.ipynb"""
   import papermill as pm

   nb = pm.read_notebook('notebook.ipynb')
   nb.display_output('matplotlib_hist')

.. image:: img/matplotlib_hist.png
