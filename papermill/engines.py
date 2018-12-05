import sys
import copy
import datetime
import dateutil

from functools import wraps
import entrypoints

from .log import logger
from .exceptions import PapermillException
from .preprocess import PapermillExecutePreprocessor
from .iorw import write_ipynb

# tqdm creates 2 globals lock which raise OSException if the execution
# environment does not have shared memory for processes, e.g. AWS Lambda
try:
    from tqdm import tqdm, tqdm_notebook

    no_tqdm = False
except OSError:
    no_tqdm = True
using_ipykernel = 'ipykernel' in sys.modules


class PapermillEngines(object):
    """
    The holder which houses any engine registered with the system.
    This object is used in a singleton manner to save and load particular
    named Engine objects for reference externally.
    """

    def __init__(self):
        self._engines = {}

    def register(self, name, engine):
        self._engines[name] = engine

    def register_entry_points(self):
        # Load handlers provided by other packages
        for entrypoint in entrypoints.get_group_all("papermill.engine"):
            self.register(entrypoint.name, entrypoint.load())

    def get_engine(self, name=None):
        """
        Retrieves an engine by name.
        """
        engine = self._engines.get(name)
        if not engine:
            raise PapermillException("No engine named '{}' found".format(name))
        return engine

    def execute_notebook_with_engine(self, engine_name, nb, kernel_name, **kwargs):
        """
        Fetches the approiate engine and executes the nb object against it.
        """
        return self.get_engine(engine_name).execute_notebook(nb, kernel_name, **kwargs)


def catch_nb_assignment(func):
    """
    Wrapper which helps catch `nb` keyword arguments and assign onto self
    when passed to the wrapped function.
    Used for callback methods when the caller may optionally have a new copy
    of the originally wrapped `nb`object.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        nb = kwargs.get('nb')
        if nb:
            # Reassign if executing notebook object was replaced
            self.nb = nb
        return func(self, *args, **kwargs)

    return wrapper


class NotebookExecutionManager(object):
    """
    This class is a wrapper for notebook objects to house execution state
    related to the notebook being run through an engine. In particular the
    NotebookExecutionManager provides common update callbacks for use within
    engines to facilitate metadata and persistence actions in a shared manner.
    """

    DEFAULT_BAR_FORMAT = "{l_bar}{bar}{r_bar}"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def __init__(self, nb, output_path=None, log_output=False, progress_bar=True):
        # Deep copy the input to isolate the object being executed against
        self.nb = copy.deepcopy(nb)
        self.output_path = output_path
        self.log_output = log_output
        self.start_time = None
        self.end_time = None
        self.pbar = None
        if progress_bar and not no_tqdm:
            self.set_pbar()

    def set_pbar(self):
        """
        Initializes the progress bar object for this notebook run.

        This is called automatically when constructed.
        """
        if using_ipykernel:
            # Load the notebook version if we're being called from a notebook
            self.pbar = tqdm_notebook(total=len(self.nb.cells))
        else:
            bar_format = self.DEFAULT_BAR_FORMAT
            if self.log_output:
                # We want to inject newlines if we're printing content between enumerations
                bar_format += "\n"
            self.pbar = tqdm(total=len(self.nb.cells), bar_format=bar_format)

    def now(self):
        return datetime.datetime.utcnow()

    def set_timer(self):
        """
        Initializes the execution timer for the notebook.

        This is called automatically when constructed.
        """
        self.start_time = self.now()
        self.end_time = None

    @catch_nb_assignment
    def save(self, **kwargs):
        """
        If an output path is known, this triggers a save of the wrapped
        notebook state to the provided path.

        Can be used outside of cell state changes if execution is taking
        a long time to conclude but the notebook object should be synced.

        e.g. you may want to save the notebook every 10 minutes when running
        a 5 hour cell execution to capture output messages in the notebook.
        """
        if self.output_path:
            write_ipynb(self.nb, self.output_path)

    @catch_nb_assignment
    def notebook_start(self, **kwargs):
        """
        Initializes and clears the metadata for the notebook and its cells, and
        saves the notebook to the output path.

        Called by Engine when execution begins.
        """
        self.set_timer()

        self.nb.metadata.papermill['start_time'] = self.start_time.isoformat()
        self.nb.metadata.papermill['end_time'] = None
        self.nb.metadata.papermill['duration'] = None
        self.nb.metadata.papermill['exception'] = None

        for cell in self.nb.cells:
            # Reset the cell execution counts.
            if cell.get("execution_count") is not None:
                cell.execution_count = None

            # Clear out the papermill metadata for each cell.
            cell.metadata.papermill = dict(
                exception=None,
                start_time=None,
                end_time=None,
                duration=None,
                status=self.PENDING,  # pending, running, completed
            )
            if cell.get("outputs") is not None:
                cell.outputs = []

        self.save()

    @catch_nb_assignment
    def cell_start(self, cell, **kwargs):
        """
        Optionally called by engines during execution to initialize the
        metadata for a cell and save the notebook to the output path.
        """
        cell.metadata.papermill['start_time'] = self.now().isoformat()
        cell.metadata.papermill["status"] = self.RUNNING
        cell.metadata.papermill['exception'] = False

        self.save()

    @catch_nb_assignment
    def cell_exception(self, cell, **kwargs):
        """
        Called by engines when an exception is raised within a notebook to
        set the metadata on the notebook indicating the location of the
        failure.
        """
        cell.metadata.papermill['exception'] = True
        cell.metadata.papermill['status'] = self.FAILED
        self.nb.metadata.papermill['exception'] = True

    @catch_nb_assignment
    def cell_complete(self, cell, **kwargs):
        """
        Optionally called by engines during execution to finalize the
        metadata for a cell and save the notebook to the output path.
        """
        end_time = self.now()
        cell.metadata.papermill['end_time'] = end_time.isoformat()
        if cell.metadata.papermill.get('start_time'):
            start_time = dateutil.parser.parse(cell.metadata.papermill['start_time'])
            cell.metadata.papermill['duration'] = (end_time - start_time).total_seconds()
        if cell.metadata.papermill['status'] != self.FAILED:
            cell.metadata.papermill['status'] = self.COMPLETED

        self.save()
        if self.pbar:
            self.pbar.update(1)

    @catch_nb_assignment
    def notebook_complete(self, **kwargs):
        """
        Finalizes the metadata for the notebook and saves the notebook to
        the output path.

        Called by Engine when execution concludes, regardless of exceptions.
        """
        self.end_time = self.now()
        self.nb.metadata.papermill['end_time'] = self.end_time.isoformat()
        if self.nb.metadata.papermill.get('start_time'):
            self.nb.metadata.papermill['duration'] = (
                self.end_time - self.start_time
            ).total_seconds()

        # Cleanup cell statuses in case callbacks were never called
        for cell in self.nb.cells:
            if cell.metadata.papermill['status'] == self.FAILED:
                break
            elif cell.metadata.papermill['status'] == self.PENDING:
                cell.metadata.papermill['status'] = self.COMPLETED

        self.complete_pbar()
        self.cleanup_pbar()

        # Force a final sync
        self.save()

    def complete_pbar(self):
        if hasattr(self, 'pbar') and self.pbar:
            self.pbar.n = len(self.nb.cells)
            self.pbar.refresh()

    def cleanup_pbar(self):
        if hasattr(self, 'pbar') and self.pbar:
            self.pbar.close()
            self.pbar = None

    def __del__(self):
        self.cleanup_pbar()


class Engine(object):
    """
    Base class from which engines should inherit and implement execute_managed_notebook.
    Defines execute_notebook method which is used to correctly setup
    the NotebookExecutionManager object for engines to interact against.
    """

    @classmethod
    def execute_notebook(
        cls, nb, kernel_name, output_path=None, progress_bar=True, log_output=False, **kwargs
    ):
        """
        Wraps the notebook object in an NotebookExecutionManager in order to track
        execution state in a uniform manner. This is meant to help simplify
        engine implementations to just focus on iterating and executing the
        cell contents.
        """
        nb_man = NotebookExecutionManager(
            nb, output_path=output_path, progress_bar=progress_bar, log_output=log_output
        )

        nb_man.notebook_start()
        try:
            nb = cls.execute_managed_notebook(nb_man, kernel_name, log_output=log_output, **kwargs)
            # Update the notebook object in case the executor didn't do it for us
            if nb:
                nb_man.nb = nb
        finally:
            nb_man.cleanup_pbar()
            nb_man.notebook_complete()

        return nb_man.nb

    @classmethod
    def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
        raise NotImplementedError("'execute_managed_notebook' is not implemented for this engine")


class NBConvertEngine(Engine):
    """
    A notebook engine which can execute a notebook document and update the
    nb_man.nb object with the results.
    """

    @classmethod
    def execute_managed_notebook(
        cls,
        nb_man,
        kernel_name,
        log_output=False,
        start_timeout=60,
        execution_timeout=None,
        **kwargs
    ):
        """
        Performs the actual execution of the parameterized notebook locally.

        Args:
            nb (NotebookNode): Executable notebook object.
            kernel_name (str): Name of kernel to execute the notebook against.
            log_output (bool): Flag for whether or not to write notebook output to stderr.
            start_timeout (int): Duration to wait for kernel start-up.
            execution_timeout (int): Duration to wait before failing execution (default: never).
        """

        # The preprocessor concept is from nbconvert, and is misleading here.
        # It actually represents a notebook processor, not a preparation object.
        preprocessor = PapermillExecutePreprocessor(
            timeout=execution_timeout,
            startup_timeout=start_timeout,
            kernel_name=kernel_name,
            log=logger,
        )
        preprocessor.log_output = log_output
        preprocessor.preprocess(nb_man, kwargs)


# Instantiate a PapermillEngines instance and register Handlers.
papermill_engines = PapermillEngines()
papermill_engines.register(None, NBConvertEngine)
papermill_engines.register('nbconvert', NBConvertEngine)
papermill_engines.register_entry_points()
