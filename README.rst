|Logo|
=========

Papermill is map reduce for jupyter notebooks.

Stepping away from the hyperbole, the goals are to assist in:

* Parametrizing notebooks
* Executing and collecting metrics across the notebooks
* Summarize collections of notebooks

Installation
------------

::

  pip install papermill


Usage
-----

::

  # Single notebook
  papermill.execute_notebook(
      notebook="template.ipynb",
      params=dict(C=-4, gamma=-4, class_weight='balanced')
  )

  # Multiple notebooks
  param_space = {'C': np.logspace(-4, 4, 9),
                 'gamma': np.logspace(-4, 4, 9),
                 'class_weight': [None, 'balanced']}
  future = papermill.sweep(
      "template.ipynb",
      param_space=param_space,
      output_dir='s3://somewhere',
      driver=papermill.LocalDriver, # If it obeys the driver interface, we know how to submit
  )


.. |Logo| image:: https://user-images.githubusercontent.com/836375/27926581-b4f3291e-623d-11e7-90f6-dd56c0fdcdfa.png
   :width: 200px
   :target: https://github.com/nteract/papermill
   :alt: Papermill
