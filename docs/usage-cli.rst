Command Line Interface
======================

papermill may be executed from the terminal. The following are the command
options:

.. code-block:: bash

    Usage: papermill [OPTIONS] NOTEBOOK_PATH OUTPUT_PATH

      This utility executes a single notebook in a subprocess.

      Papermill takes a source notebook, applies parameters to the source
      notebook, executes the notebook with the specified kernel, and saves the
      output in the destination notebook.

      The NOTEBOOK_PATH and OUTPUT_PATH can now be replaced by `-` representing
      stdout and stderr, or by the presence of pipe inputs / outputs. Meaning
      that

      `<generate input>... | papermill | ...<process output>`

      with `papermill - -` being implied by the pipes will read a notebook from
      stdin and write it out to stdout.

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
      --request-save-on-cell-execute / --no-request-save-on-cell-execute
                                      Request save notebook after each cell
                                      execution
      --prepare-only / --prepare-execute
                                      Flag for outputting the notebook without
                                      execution, but with parameters applied.
      -k, --kernel TEXT               Name of kernel to run.
      --cwd TEXT                      Working directory to run notebook in.
      --progress-bar / --no-progress-bar
                                      Flag for turning on the progress bar.
      --log-output / --no-log-output  Flag for writing notebook output to the
                                      configured logger.
      --stdout-file FILENAME          File to write notebook stdout output to.
      --stderr-file FILENAME          File to write notebook stderr output to.
      --log-level [NOTSET|DEBUG|INFO|WARNING|ERROR|CRITICAL]
                                      Set log level
      --start-timeout INTEGER         Time in seconds to wait for kernel to start.
      --execution-timeout INTEGER     Time in seconds to wait for each cell before
                                      failing execution (default: forever)
      --report-mode / --no-report-mode
                                      Flag for hiding input.
      --version                       Flag for displaying the version.
      -h, --help                      Show this message and exit.
