"""Engines to perform different roles"""
import sys
import copy
import datetime
import dateutil

from functools import wraps
import entrypoints

from .log import logger
from .exceptions import PapermillException
from .clientwrap import PapermillNotebookClient
from .iorw import write_ipynb
from .utils import merge_kwargs, remove_args


class PapermillEngines(object):
    """
    The holder which houses any engine registered with the system.

    This object is used in a singleton manner to save and load particular
    named Engine objects so they may be referenced externally.
    """

    def __init__(self):
        self._engines = {}

    def register(self, name, engine):
        """Register a named engine"""
        self._engines[name] = engine

    def register_entry_points(self):
        """Register entrypoints for an engine

        Load handlers provided by other packages
        """
        for entrypoint in entrypoints.get_group_all("papermill.engine"):
            self.register(entrypoint.name, entrypoint.load())

    def get_engine(self, name=None):
        """Retrieves an engine by name."""
        engine = self._engines.get(name)
        if not engine:
            raise PapermillException("No engine named '{}' found".format(name))
        return engine

    def execute_notebook_with_engine(self, engine_name, nb, kernel_name, **kwargs):
        """Fetch a named engine and execute the nb object against it."""
        return self.get_engine(engine_name).execute_notebook(nb, kernel_name, **kwargs)


def catch_nb_assignment(func):
    """
    Wrapper to catch `nb` keyword arguments

    This helps catch `nb` keyword arguments and assign onto self when passed to
    the wrapped function.

    Used for callback methods when the caller may optionally have a new copy
    of the originally wrapped `nb` object.
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
    Wrapper for execution state of a notebook.

    This class is a wrapper for notebook objects to house execution state
    related to the notebook being run through an engine.

    In particular the NotebookExecutionManager provides common update callbacks
    for use within engines to facilitate metadata and persistence actions in a
    shared manner.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def __init__(
        self, nb, output_path=None, log_output=False, progress_bar=True, autosave_cell_every=30
    ):
        # Deep copy the input to isolate the object being executed against
        self.nb = copy.deepcopy(nb)
        self.output_path = output_path
        self.log_output = log_output
        self.start_time = None
        self.end_time = None
        self.autosave_cell_every = autosave_cell_every
        self.max_autosave_pct = 25
        self.last_save_time = self.now()  # Not exactly true, but simplifies testing logic
        self.pbar = None
        if progress_bar:
            # lazy import due to implict slow ipython import
            from tqdm.auto import tqdm

            self.pbar = tqdm(total=len(self.nb.cells), unit="cell", desc="Executing")

    def now(self):
        """Helper to return current UTC time"""
        return datetime.datetime.utcnow()

    def set_timer(self):
        """
        Initializes the execution timer for the notebook.

        This is called automatically when a NotebookExecutionManager is
        constructed.
        """
        self.start_time = self.now()
        self.end_time = None

    @catch_nb_assignment
    def save(self, **kwargs):
        """
        Saves the wrapped notebook state.

        If an output path is known, this triggers a save of the wrapped
        notebook state to the provided path.

        Can be used outside of cell state changes if execution is taking
        a long time to conclude but the notebook object should be synced.

        For example, you may want to save the notebook every 10 minutes when running
        a 5 hour cell execution to capture output messages in the notebook.
        """
        if self.output_path:
            write_ipynb(self.nb, self.output_path)
        self.last_save_time = self.now()

    @catch_nb_assignment
    def autosave_cell(self):
        """Saves the notebook if it's been more than self.autosave_cell_every seconds
        since it was last saved.
        """
        if self.autosave_cell_every == 0:
            # feature is disabled
            return
        time_since_last_save = (self.now() - self.last_save_time).total_seconds()
        if time_since_last_save >= self.autosave_cell_every:
            start_save = self.now()
            self.save()
            save_elapsed = (self.now() - start_save).total_seconds()
            if save_elapsed > self.autosave_cell_every * self.max_autosave_pct / 100.0:
                # Autosave is taking too long, so exponentially back off.
                self.autosave_cell_every *= 2
                logger.warning(
                    "Autosave too slow: {:.2f} sec, over {}% limit. Backing off to {} sec".format(
                        save_elapsed, self.max_autosave_pct, self.autosave_cell_every
                    )
                )

    @catch_nb_assignment
    def notebook_start(self, **kwargs):
        """
        Initialize a notebook, clearing its metadata, and save it.

        When starting a notebook, this initializes and clears the metadata for
        the notebook and its cells, and saves the notebook to the given
        output path.

        Called by Engine when execution begins.
        """
        self.set_timer()

        self.nb.metadata.papermill['start_time'] = self.start_time.isoformat()
        self.nb.metadata.papermill['end_time'] = None
        self.nb.metadata.papermill['duration'] = None
        self.nb.metadata.papermill['exception'] = None

        for cell in self.nb.cells:
            # Reset the cell execution counts.
            if cell.get("cell_type") == "code":
                cell.execution_count = None

            # Clear out the papermill metadata for each cell.
            cell.metadata.papermill = dict(
                exception=None,
                start_time=None,
                end_time=None,
                duration=None,
                status=self.PENDING,  # pending, running, completed
            )
            if cell.get("cell_type") == "code":
                cell.outputs = []

        self.save()

    @catch_nb_assignment
    def cell_start(self, cell, cell_index=None, **kwargs):
        """
        Set and save a cell's start state.

        Optionally called by engines during execution to initialize the
        metadata for a cell and save the notebook to the output path.
        """
        if self.log_output:
            ceel_num = cell_index + 1 if cell_index is not None else ''
            logger.info('Executing Cell {:-<40}'.format(ceel_num))

        cell.metadata.papermill['start_time'] = self.now().isoformat()
        cell.metadata.papermill["status"] = self.RUNNING
        cell.metadata.papermill['exception'] = False

        self.save()

    @catch_nb_assignment
    def cell_exception(self, cell, cell_index=None, **kwargs):
        """
        Set metadata when an exception is raised.

        Called by engines when an exception is raised within a notebook to
        set the metadata on the notebook indicating the location of the
        failure.
        """
        cell.metadata.papermill['exception'] = True
        cell.metadata.papermill['status'] = self.FAILED
        self.nb.metadata.papermill['exception'] = True

    @catch_nb_assignment
    def cell_complete(self, cell, cell_index=None, **kwargs):
        """
        Finalize metadata for a cell and save notebook.

        Optionally called by engines during execution to finalize the
        metadata for a cell and save the notebook to the output path.
        """
        end_time = self.now()

        if self.log_output:
            ceel_num = cell_index + 1 if cell_index is not None else ''
            logger.info('Ending Cell {:-<43}'.format(ceel_num))
            # Ensure our last cell messages are not buffered by python
            sys.stdout.flush()
            sys.stderr.flush()

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
        Finalize the metadata for a notebook and save the notebook to
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
        """Refresh progress bar"""
        if hasattr(self, 'pbar') and self.pbar:
            self.pbar.n = len(self.nb.cells)
            self.pbar.refresh()

    def cleanup_pbar(self):
        """Clean up a progress bar"""
        if hasattr(self, 'pbar') and self.pbar:
            self.pbar.close()
            self.pbar = None

    def __del__(self):
        self.cleanup_pbar()


class Engine(object):
    """
    Base class for engines.

    Other specific engine classes should inherit and implement the
    `execute_managed_notebook` method.

    Defines `execute_notebook` method which is used to correctly setup
    the `NotebookExecutionManager` object for engines to interact against.
    """

    @classmethod
    def execute_notebook(
        cls,
        nb,
        kernel_name,
        output_path=None,
        progress_bar=True,
        log_output=False,
        autosave_cell_every=30,
        **kwargs
    ):
        """
        A wrapper to handle notebook execution tasks.

        Wraps the notebook object in a `NotebookExecutionManager` in order to track
        execution state in a uniform manner. This is meant to help simplify
        engine implementations. This allows a developer to just focus on
        iterating and executing the cell contents.
        """
        nb_man = NotebookExecutionManager(
            nb,
            output_path=output_path,
            progress_bar=progress_bar,
            log_output=log_output,
            autosave_cell_every=autosave_cell_every,
        )

        nb_man.notebook_start()
        try:
            cls.execute_managed_notebook(nb_man, kernel_name, log_output=log_output, **kwargs)
        finally:
            nb_man.cleanup_pbar()
            nb_man.notebook_complete()

        return nb_man.nb

    @classmethod
    def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
        """An abstract method where implementation will be defined in a subclass."""
        raise NotImplementedError("'execute_managed_notebook' is not implemented for this engine")


class NBClientEngine(Engine):
    """
    A notebook engine representing an nbclient process.

    This can execute a notebook document and update the `nb_man.nb` object with
    the results.
    """

    @classmethod
    def execute_managed_notebook(
        cls,
        nb_man,
        kernel_name,
        log_output=False,
        stdout_file=None,
        stderr_file=None,
        start_timeout=60,
        execution_timeout=None,
        **kwargs
    ):
        """
        Performs the actual execution of the parameterized notebook locally.

        Args:
            nb (NotebookNode): Executable notebook object.
            kernel_name (str): Name of kernel to execute the notebook against.
            log_output (bool): Flag for whether or not to write notebook output to the
                               configured logger.
            start_timeout (int): Duration to wait for kernel start-up.
            execution_timeout (int): Duration to wait before failing execution (default: never).
        """

        # Exclude parameters that named differently downstream
        safe_kwargs = remove_args(['timeout', 'startup_timeout'], **kwargs)

        # Nicely handle preprocessor arguments prioritizing values set by engine
        final_kwargs = merge_kwargs(
            safe_kwargs,
            timeout=execution_timeout if execution_timeout else kwargs.get('timeout'),
            startup_timeout=start_timeout,
            kernel_name=kernel_name,
            log=logger,
            log_output=log_output,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
        )
        return PapermillNotebookClient(nb_man, **final_kwargs).execute()


# Instantiate a PapermillEngines instance, register Handlers and entrypoints
papermill_engines = PapermillEngines()
papermill_engines.register(None, NBClientEngine)
papermill_engines.register('nbclient', NBClientEngine)
papermill_engines.register_entry_points()
