|Logo|
=========

Papermill is a tool for parameterizing, executing, and analyzing Jupyter Notebooks.

The goals for Papermill are:

* Parametrizing notebooks
* Executing and collecting metrics across the notebooks
* Summarizing collections of notebooks

Installation
------------

::

  pip install papermill


Usage
-----

Parameterizing a notebook.

.. code-block:: python

   ### template.ipynb
   # This cell has a "parameters" tag. These values will be overwritten by Papermill.
   alpha = 0.5
   ratio = 0.1


Recording values to be saved with the notebook.

.. code-block:: python

   ### template.ipynb
   import random
   import papermill as pm

   rand_value = random.randint(1, 10)
   pm.record("random_value", rand_value)
   pm.record("foo", "bar")

Displaying outputs to be saved with the notebook.

.. code-block:: python

   ### template.ipynb
   # Import plt and turn off interactive plotting to avoid double plotting.
   import papermill as pm
   import matplotlib.pyplot as plt; plt.ioff()
   from ggplot import mpg

   f = plt.figure()
   plt.hist('cty', bins=12, data=mpg)
   pm.display('matplotlib_hist', f)



Executing a parameterized Jupyter notebook

.. code-block:: python

    import papermill as pm

    pm.execute_notebook(
        notebook="template.ipynb",
        output="output.ipynb",
        params=dict(alpha=0.1, ratio=0.001)
    )

Analyzing a single notebook

.. code-block:: python

   ### summary.ipynb
   import papermill as pm

   nb = pm.read_notebook('output.ipynb')
   nb.dataframe.head()

   # Show named plot from 'output.ipynb'
   nb.display_output('matplotlib_hist')


Analyzing a collection of notebooks

.. code-block:: python

   ### summary.ipynb
   import papermill as pm

   nbs = pm.read_notebooks('/path/to/results/')

   # Show named plot from 'output1.ipynb'
   nbs.display_output('output1.ipynb', 'matplotlib_hist')

   # Dataframe for all notebooks in collection
   df = nbs.dataframe
   df.head()

   # Show histograms from notebooks with the highest random value.
   pivoted_df = df.pivot('key', 'name', 'value').sort_values(by='name')
   pivoted_df.head()

   nbs.display_output(pivoted_df[:3], 'matplotlib_hist')

.. |Logo| image:: https://user-images.githubusercontent.com/836375/27929844-6bb34e62-6249-11e7-9a2a-00849a64940c.png
   :width: 200px
   :target: https://github.com/nteract/papermill
   :alt: Papermill
