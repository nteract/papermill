Troubleshooting
===============

NoSuchKernel Errors (using Conda)
---------------------------------

NoSuchKernel Errors can appear when running papermill on jupyter notebooks whose
kernel as been specified via conda (nb_conda). nb_conda is used to easily set
conda environment per notebook from within jupyterlab.

To illustrate, let us create a new environment with all the dependencies
necessary for an analysis, for example here, a simple R notebook:

``conda create -n analysis_1 r-essentials``

Once nb_conda is used within the jupyter server to set the kernel for this
notebook to *analysis_1*, the notebook gets metadata similar to the following:

::
   
   "metadata": {
   "kernelspec": {
       "display_name": "R [conda env:analysis_1]",
       "language": "R",
       "name": "conda-env-analysis_1-r"
   } ...

Using papermill from the *analysis_1* environment or another environment will not work and return the following error:

::

   jupyter_client.kernelspec.NoSuchKernel: No such kernel named conda-env-analysis_1-r

This can be fixed by :

* Installing jupyter and papermill in the analysis environment *analysis_1*:

``conda install -n analysis_1 jupyter papermill``

* Specifying the name of the kernel to use from within this environment *analysis_1* in the papermill command (**-k** option):

To find the kernels available from this environment:

``conda activate analysis_1``

``(analysis_1)$ jupyter kernelspec list``

::
   
   Available kernels:
   ir         PATH/TO/ir
   python3    PATH/TO/python3

To use the kernel needed from within the *analysis_1* environment:

``conda activate analysis_1``

``(analysis_1)$ papermill my_notebook.ipynb output_notebook.ipynb -k ir``
