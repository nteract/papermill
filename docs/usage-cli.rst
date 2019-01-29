Command Line Interface
======================

papermill may be executed from the terminal. The following are the command
options:

.. code-block:: bash

    Usage: papermill [OPTIONS] NOTEBOOK_PATH OUTPUT_PATH

      This utility executes a single notebook on a container.

      Papermill takes a source notebook, applies parameters to the source
      notebook, executes the notebook with the specified kernel, and saves the
      output in the destination notebook.

    Options:
      -p, --parameters TEXT...        Parameters to pass to the parameters cell.
      -r, --parameters_raw TEXT...    Parameters to be read as raw string.
      -f, --parameters_file TEXT      Path to YAML file containing parameters.
      -y, --parameters_yaml TEXT      YAML string to be used as parameters.
      -b, --parameters_base64 TEXT    Base64 encoded YAML string as parameters.
      --inject-input-path             Insert the path of the input notebook as
                                      PAPERMILL_INPUT_PATH as a notebook
                                      parameter.
      --inject-output-path            Insert the path of the output notebook as
                                      PAPERMILL_OUTPUT_PATH as a notebook
                                      parameter.
      --inject-paths                  Insert the paths of input/output notebooks
                                      as
                                      PAPERMILL_INPUT_PATH/PAPERMILL_OUTPUT_PATH
                                      as notebook parameters.
      --engine TEXT                   The execution engine name to use in
                                      evaluating the notebook.
      --prepare-only / --prepare-execute
                                      Flag for outputting the notebook without
                                      execution, but with parameters applied.
      -k, --kernel TEXT               Name of kernel to run.
      --cwd TEXT                      Working directory to run notebook in.
      --progress-bar / --no-progress-bar
                                      Flag for turning on the progress bar.
      --log-output / --no-log-output  Flag for writing notebook output to stderr.
      --log-level [NOTSET|DEBUG|INFO|WARNING|ERROR|CRITICAL]
                                      Set log level
      --start_timeout INTEGER         Time in seconds to wait for kernel to start.
      --report-mode / --not-report-mode
                                      Flag for hiding input.
      --version                       Flag for displaying the version.
      -h, --help                      Show this message and exit.
