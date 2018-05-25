from __future__ import unicode_literals, print_function

import datetime

from concurrent import futures
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors.execute import CellExecutionError

from .iorw import write_ipynb

# tqdm creates 2 globals lock which raise OSException if the execution
# environment does not have shared memory for processes, e.g. AWS Lambda
try:
    from tqdm import tqdm
    no_tqdm = False
except OSError:
    no_tqdm = True

PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"


class PapermillExecutePreprocessor(ExecutePreprocessor):
    """Module containing a preprocessor that executes the code cells
    and updates outputs"""

    # Copyright (c) IPython Development Team.
    # Distributed under the terms of the Modified BSD License.

    # TODO: Delete this wrapper when nbconvert allows for setting preprocessor
    # hood in a more convienent manner
    def preprocess(self, nb, resources):
        """
        Copied with one edit of super -> papermill_preprocessor from nbconvert

        Preprocess notebook executing each code cell.

        The input argument `nb` is modified in-place.

        Parameters
        ----------
        nb : NotebookNode
            Notebook being executed.
        resources : dictionary
            Additional resources used in the conversion process. For example,
            passing ``{'metadata': {'path': run_path}}`` sets the
            execution path to ``run_path``.

        Returns
        -------
        nb : NotebookNode
            The executed notebook.
        resources : dictionary
            Additional resources used in the conversion process.
        """
        path = resources.get('metadata', {}).get('path') or None

        # clear display_id map
        self._display_id_map = {}

        kernel_name = nb.metadata.get('kernelspec', {}).get('name', 'python')
        if self.kernel_name:
            kernel_name = self.kernel_name
        self.log.info("Executing notebook with kernel: %s" % kernel_name)
        self.km, self.kc = self.start_new_kernel(
            startup_timeout=self.startup_timeout,
            kernel_name=kernel_name,
            extra_arguments=self.extra_arguments,
            cwd=path)
        self.kc.allow_stdin = False
        # Parent class requires self.nb to be present temporarily during preproc
        self.nb = nb

        try:
            nb, resources = self.papermill_preprocess(nb, resources)
        finally:
            self.kc.stop_channels()
            self.km.shutdown_kernel(now=self.shutdown_kernel == 'immediate')
            # Parent class required self.nb be removed after preproc
            delattr(self, 'nb')

        return nb, resources

    def start_new_kernel(self, startup_timeout=60, kernel_name='python', **kwargs):
        km = self.kernel_manager_class(kernel_name=kernel_name)
        km.start_kernel(**kwargs)
        kc = km.client()
        kc.start_channels()
        try:
            kc.wait_for_ready(timeout=startup_timeout)
        except RuntimeError:
            kc.stop_channels()
            km.shutdown_kernel()
            raise

        return km, kc

    def papermill_preprocess(self, nb, resources):
        """
        This function acts as a replacement for the grandparent's `preprocess`
        method.

        We are doing this for the following reasons:

        1. Notebooks will stop executing when they encounter a failure but not
           raise a `CellException`. This allows us to save the notebook with the
           traceback even though a `CellExecutionError` was encountered.

        2. We want to write the notebook as cells are executed. We inject our
           logic for that here.

        3. We want to include timing and execution status information with the
           metadata of each cell.

        Parameters
        ----------
        nb : NotebookNode
            Notebook being converted
        resources : dictionary
            Additional resources used in the conversion process.  Allows
            preprocessors to pass variables into the Jinja engine.

        """
        output_path = nb.metadata.papermill['output_path']

        # Reset the notebook.
        for cell in nb.cells:
            # Reset the cell execution counts.
            if cell.get("execution_count") is not None:
                cell.execution_count = None

            # Clear out the papermill metadata for each cell.
            cell.metadata['papermill'] = dict(
                exception=None,
                start_time=None,
                end_time=None,
                duration=None,
                status=PENDING  # pending, running, completed
            )
            if cell.get("outputs") is not None:
                cell.outputs = []

        # Execute each cell and update the output in real time.
        with futures.ThreadPoolExecutor(max_workers=1) as executor:

            # Generate the iterator
            if self.progress_bar:
                execution_iterator = tqdm(enumerate(nb.cells), total=len(nb.cells))
            else:
                execution_iterator = enumerate(nb.cells)

            for index, cell in execution_iterator:
                cell.metadata["papermill"]["status"] = RUNNING
                future = executor.submit(write_ipynb, nb, output_path)
                t0 = datetime.datetime.utcnow()
                try:
                    if not cell.source:
                        continue

                    nb.cells[index], resources = self.preprocess_cell(
                        cell, resources, index)
                    cell.metadata['papermill']['exception'] = False
                    if self.log_output:
                        log_outputs(nb.cells[index])

                except CellExecutionError:
                    cell.metadata['papermill']['exception'] = True
                    break
                finally:
                    t1 = datetime.datetime.utcnow()
                    cell.metadata['papermill']['start_time'] = t0.isoformat()
                    cell.metadata['papermill']['end_time'] = t1.isoformat()
                    cell.metadata['papermill']['duration'] = (
                        t1 - t0).total_seconds()
                    cell.metadata['papermill']['status'] = COMPLETED
                    future.result()
        return nb, resources
