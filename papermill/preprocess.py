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


class PapermillExecutePreprocessor(ExecutePreprocessor):
    """Module containing a preprocessor that executes the code cells
    and updates outputs"""

    def preprocess(self, nb_man, resources, km=None):
        """
        Wraps the parent class process call slightly
        """
        with self.setup_preprocessor(nb_man.nb, resources, km=km):
            if self.log_output:
                self.log.info("Executing notebook with kernel: %s" % self.kernel_name)
            nb, resources = self.papermill_process(nb_man, resources)
            info_msg = self._wait_for_reply(self.kc.kernel_info())
            nb.metadata['language_info'] = info_msg['content']['language_info']

        return nb, resources

    def start_new_kernel(self, **kwargs):
        """
        Wraps the parent class process call slightly
        """
        km, kc = super(PapermillExecutePreprocessor, self).start_new_kernel(**kwargs)
        # Note sure if we need this anymore?
        kc.allow_stdin = False

        return km, kc

    def papermill_process(self, nb_man, resources):
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
        nb_man : NotebookExecutionManager
            Engine wrapper of notebook being converted
        resources : dictionary
            Additional resources used in the conversion process.  Allows
            preprocessors to pass variables into the Jinja engine.

        """
        # Execute each cell and update the output in real time.
        nb = nb_man.nb
        for index, cell in enumerate(nb.cells):
            try:
                nb_man.cell_start(cell)
                if not cell.source:
                    continue
                nb.cells[index], resources = self.preprocess_cell(cell, resources, index)
            except CellExecutionError as ex:
                nb_man.cell_exception(nb.cells[index], exception=ex)
                break
            finally:
                nb_man.cell_complete(nb.cells[index])
        return nb, resources

    def log_output_message(self, output):
        if output.output_type == "stream":
            if output.name == "stdout":
                self.log.info("".join(output.text))
            elif output.name == "stderr":
                # In case users want to redirect stderr differently, pipe to warning
                self.log.warning("".join(output.text))
        elif "data" in output and "text/plain" in output.data:
            self.log.info("".join(output.data['text/plain']))
        # Force a flush to avoid long python buffering for messages
        sys.stdout.flush()
        sys.stderr.flush()

    # TODO: Update nbconvert to allow for msg yielding so we can log as messages arrive
    def run_cell(self, cell, cell_index=0):
        msg_id = self.kc.execute(cell.source)
        # Log check added to original implementation
        if self.log_output:
            self.log.info('Executing Cell {:-<40}'.format(cell_index + 1))
        self.log.debug("Executing cell contents:\n%s", cell.source)
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

            # Log check added to original implementation
            if self.log_output:
                self.log_output_message(out)
            outs.append(out)

        exec_reply = self._wait_for_reply(msg_id, cell)
        # Log check added to original implementation
        if self.log_output:
            self.log.info('Ending Cell {:-<43}'.format(cell_index + 1))
            # Ensure our last cell messages are not buffered by python
            sys.stdout.flush()
            sys.stderr.flush()

        return exec_reply, outs
