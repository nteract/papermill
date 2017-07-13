|Logo|
=========

Papermill is map reduce for Jupyter notebooks.

Stepping away from the hyperbole, our goals for Papermill include simplifying
and streamlining:

* Parametrizing notebooks
* Executing and collecting metrics across the notebooks
* Summarize collections of notebooks

Installation
------------

::

  pip install papermill


Usage
-----

Executing a parametrized notebook

.. code-block:: python

    import papermill as pm

    pm.execute_notebook(
        notebook="template.ipynb",
        output="output.ipynb",
        params=dict(alpha=0.1, ratio=0.001)
    )

    nb = pm.read_notebook("output.ipynb")

Creating a parametrized notebook and record metrics


.. code-block:: python

    ### template.ipynb
    import papermill as pm

    rmse = metrics.mean_squared_error(...)
    pm.record_value("rmse", rmse)
    plot() # Tag this cell as "results" for extraction later

.. code-block:: python

    ### run_and_summarize.ipynb
    pm.execute_notebook(
        notebook="template.ipynb",
        output="output.ipynb",
        params=dict(alpha=0.1, ratio=0.001)
    )

    # Print RMSE value saved in "output.ipynb"
    nb = pm.read_notebook("output.ipynb")
    nb_data = pm.fetch_notebook_data(nb)
    print("rmse", nb_data["rmse"])

    # Show plot found in "output.ipynb"
    result_cell = pm.get_tagged_cell(nb, "results")
    plot = pm.get_image_from_cell(result_cell)
    pm.display_image(plot)


.. |Logo| image:: https://user-images.githubusercontent.com/836375/27929844-6bb34e62-6249-11e7-9a2a-00849a64940c.png
   :width: 200px
   :target: https://github.com/nteract/papermill
   :alt: Papermill
