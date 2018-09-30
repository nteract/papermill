from __future__ import unicode_literals, print_function
from future.utils import raise_from  # noqa: F401

import sys

from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors.execute import CellExecutionError
from nbformat.v4 import output_from_msg

try:
    from queue import Empty  # Py 3
except ImportError:
    from Queue import Empty  # Py 2


def log_output(output):
    if output.output_type == "stream":
        if output.name == "stdout":
            sys.stdout.write("".join(output.text))
        elif output.name == "stderr":
            sys.stderr.write("".join(output.text))
    elif "data" in output and "text/plain" in output.data:
        sys.stdout.write("".join(output.data['text/plain']) + "\n")
    # Force a flush to avoid long python buffering for messages
    sys.stdout.flush()
    sys.stderr.flush()


class PapermillExecutePreprocessor(ExecutePreprocessor):
    """Module containing a preprocessor that executes the code cells
    and updates outputs"""

    # Copyright (c) IPython Development Team.
    # Distributed under the terms of the Modified BSD License.

    # TODO: Delete this wrapper and push shared changes to nbconvert

    def preprocess(self, engine_nb, resources):
        """
        Copied with one edit of super -> papermill_preprocessor from nbconvert

        Preprocess notebook executing each code cell.

        The input argument `nb` is modified in-place.

        Parameters
        ----------
        engine_nb : EngineNotebookWrapper
            Wrapped notebook being executed.
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
        nb = engine_nb.nb
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
            cwd=path,
        )
        self.kc.allow_stdin = False
        # Parent class requires self.nb to be present temporarily during preproc
        self.nb = nb

        try:
            nb, resources = self.papermill_process(engine_nb, resources)
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

    def papermill_process(self, engine_nb, resources):
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
        engine_nb : EngineNotebookWrapper
            Engine wrapper of notebook being converted
        resources : dictionary
            Additional resources used in the conversion process.  Allows
            preprocessors to pass variables into the Jinja engine.

        """
        # Execute each cell and update the output in real time.
        nb = engine_nb.nb
        for index, cell in enumerate(nb.cells):
            try:
                engine_nb.cell_start(cell)
                if not cell.source:
                    continue
                nb.cells[index], resources = self.preprocess_cell(cell, resources, index)
            except CellExecutionError as ex:
                engine_nb.cell_exception(nb.cells[index], exception=ex)
                break
            finally:
                engine_nb.cell_complete(nb.cells[index])
        return nb, resources

    def run_cell(self, cell, cell_index=0):
        msg_id = self.kc.execute(cell.source)
        self.log.debug("Executing cell:\n%s", cell.source)
        outs = cell.outputs = []

        while True:
            try:
                # We are not waiting for execute_reply, so all output
                # will not be waiting for us. This may produce currently unknown issues.
                msg = self.kc.iopub_channel.get_msg(timeout=None)
            except Empty:
                self.log.warning("Timeout waiting for IOPub output")
                if self.raise_on_iopub_timeout:
                    raise RuntimeError("Timeout waiting for IOPub output")
                else:
                    break
            if msg['parent_header'].get('msg_id') != msg_id:
                # not an output from our execution
                continue

            msg_type = msg['msg_type']
            self.log.debug("output: %s", msg_type)
            content = msg['content']

            # set the prompt number for the input and the output
            if 'execution_count' in content:
                cell['execution_count'] = content['execution_count']

            if msg_type == 'status':
                if content['execution_state'] == 'idle':
                    break
                else:
                    continue
            elif msg_type == 'execute_input':
                if self.log_output:
                    sys.stdout.write(
                        'Executing Cell {:-<40}\n'.format(content.get("execution_count", "*"))
                    )
                continue
            elif msg_type == 'clear_output':
                outs[:] = []
                # clear display_id mapping for this cell
                for display_id, cell_map in self._display_id_map.items():
                    if cell_index in cell_map:
                        cell_map[cell_index] = []
                continue
            elif msg_type.startswith('comm'):
                continue

            display_id = None
            if msg_type in {'execute_result', 'display_data', 'update_display_data'}:
                display_id = msg['content'].get('transient', {}).get('display_id', None)
                if display_id:
                    self._update_display_id(display_id, msg)
                if msg_type == 'update_display_data':
                    # update_display_data doesn't get recorded
                    continue

            try:
                out = output_from_msg(msg)
            except ValueError:
                self.log.error("unhandled iopub msg: " + msg_type)
                continue
            if display_id:
                cell_map = self._display_id_map.setdefault(display_id, {})
                output_idx_list = cell_map.setdefault(cell_index, [])
                output_idx_list.append(len(outs))

            if self.log_output:
                log_output(out)
            outs.append(out)

        exec_reply = self._wait_for_reply(msg_id, cell)
        if self.log_output:
            sys.stdout.write(
                'Ending Cell {:-<43}\n'.format(
                    exec_reply.get("content", {}).get("execution_count", content)
                )
            )
            # Ensure our last cell messages are not buffered by python
            sys.stdout.flush()

        return exec_reply, outs
