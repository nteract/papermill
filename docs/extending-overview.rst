Extending papermill
===================

Papermill provides some interfaces with external services out of the box.
However, you may find that you would like papermill to do more than it currently
does. You could contribute to the papermill project yourself (see
:ref:`developing-papermill`). However, an easier method might be to extend
papermill using `entry points`_.

In general, when you run a notebook with papermill, the following happens:

1. The notebook file is read in
2. The file content is converted to a notebook python object
3. The notebook is executed
4. The notebook is written to a file

Through entry points, you can write your own tools to handle steps 1, 3, and 4.
If you find that there's more you want to contribute to papermill, consider
developing papermill itself.

.. toctree::
   :maxdepth: 2

   extending-entry-points
   extending-developing


.. _`entry points`: https://packaging.python.org/specifications/entry-points/
