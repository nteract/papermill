Troubleshooting
===============

NoSuchKernel Errors (using Conda)
---------------------------------

NoSuchKernel Errors can appear when running papermill on jupyter notebooks whose
kernel has been specified via conda (nb_conda). nb_conda is used to easily set
conda environment per notebook from within jupyterlab.

To illustrate, let us create a new environment with all the dependencies
necessary for an analysis, for example here, a simple Python notebook:

``conda create -n analysis_1 python=2 ipykernel``

Once nb_conda is used within the jupyter server to set the kernel for this
notebook to *analysis_1*, the notebook gets metadata similar to the following:

.. code-block:: json

  {
   "kernelspec": {
    "display_name": "Python [conda env:analysis_1]",
    "language": "python",
    "name": "conda-env-analysis_1-py"
   }
  }

Using papermill (from *analysis_1* or another environment) will not work and return the following error:

``jupyter_client.kernelspec.NoSuchKernel: No such kernel named conda-env-analysis_1-py``

This can be fixed by:

* Installing jupyter
  (`or at least ipykernel <https://ipython.readthedocs.io/en/stable/install/kernel_install.html#kernels-for-different-environments>`_)
  in *analysis_1*

``conda install -n analysis_1 jupyter``

* Expose the *analysis_1* environment as a jupyter kernel
  (`this is no longer automatic <https://github.com/jupyter/jupyter/issues/245>`_).

::

   conda activate analysis_1
   jupyter kernelspec install --user --name analysis_1

* Run papermill (from any environment) specifying the correct kernel using the ``-k`` option

``papermill my_notebook.ipynb output_notebook.ipynb -k analysis_1``
