Display
=======

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
