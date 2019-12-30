from __future__ import unicode_literals, print_function

from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors.execute import CellExecutionError
from traitlets import Bool, Instance


class PapermillExecutePreprocessor(ExecutePreprocessor):
    """Module containing a preprocessor that executes the code cells
    and updates outputs"""

    log_output = Bool(False).tag(config=True)
    stdout_file = Instance(object, default_value=None).tag(config=True)
    stderr_file = Instance(object, default_value=None).tag(config=True)

    def preprocess(self, nb_man, resources, km=None):
        """
        Wraps the parent class process call slightly
        """
        with self.setup_preprocessor(nb_man.nb, resources, km=km):
            if self.log_output:
                self.log.info("Executing notebook with kernel: {}".format(self.kernel_name))
            nb, resources = self.papermill_process(nb_man, resources)
            info_msg = self._wait_for_reply(self.kc.kernel_info())
            nb.metadata['language_info'] = info_msg['content']['language_info']
            self.set_widgets_metadata()

        return nb, resources

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
        self.current_nb_man = nb_man
        for index, cell in enumerate(nb.cells):
            try:
                nb_man.cell_start(cell, index)
                if not cell.source:
                    continue
                nb.cells[index], resources = self.preprocess_cell(cell, resources, index)
            except CellExecutionError as ex:
                nb_man.cell_exception(nb.cells[index], cell_index=index, exception=ex)
                break
            finally:
                nb_man.cell_complete(nb.cells[index], cell_index=index)
        return nb, resources

    def log_output_message(self, output):
        """
        Process a given output. May log it in the configured logger and/or write it into
        the configured stdout/stderr files.

        :param output: nbformat.notebooknode.NotebookNode
        :return:
        """
        if output.output_type == "stream":
            content = "".join(output.text)
            if output.name == "stdout":
                if self.log_output:
                    self.log.info(content)
                if self.stdout_file:
                    self.stdout_file.write(content)
                    self.stdout_file.flush()
            elif output.name == "stderr":
                if self.log_output:
                    # In case users want to redirect stderr differently, pipe to warning
                    self.log.warning(content)
                if self.stderr_file:
                    self.stderr_file.write(content)
                    self.stderr_file.flush()
        elif self.log_output and ("data" in output and "text/plain" in output.data):
            self.log.info("".join(output.data['text/plain']))

    def process_message(self, *arg, **kwargs):
        output = super(PapermillExecutePreprocessor, self).process_message(*arg, **kwargs)
        self.current_nb_man.autosave_cell()
        if output and (self.log_output or self.stderr_file or self.stdout_file):
            self.log_output_message(output)
        return output
