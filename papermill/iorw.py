# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io
import os
import json
import yaml
import fnmatch
import nbformat
import requests
import warnings
import entrypoints

from contextlib import contextmanager

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from . import __version__
from .log import logger
from .utils import chdir
from .exceptions import (
    PapermillException,
    PapermillRateLimitException,
    missing_dependency_generator,
    missing_environment_variable_generator,
)

try:
    from .s3 import S3
except ImportError:
    S3 = missing_dependency_generator("boto3", "s3")
try:
    from .adl import ADL
except ImportError:
    ADL = missing_dependency_generator("azure.datalake.store", "azure")
except KeyError as exc:
    if exc.args[0] == "APPDATA":
        ADL = missing_environment_variable_generator("azure.datalake.store", "APPDATA")
    else:
        raise
try:
    from .abs import AzureBlobStore
except ImportError:
    AzureBlobStore = missing_dependency_generator("azure.storage.blob", "azure")
try:
    from gcsfs import GCSFileSystem
except ImportError:
    GCSFileSystem = missing_dependency_generator("gcsfs", "gcs")

# Handle newer and older gcsfs versions
try:
    try:
        from gcsfs.utils import HttpError as GCSHttpError
    except ImportError:
        from gcsfs.utils import HtmlError as GCSHttpError
except ImportError:
    # Fall back to a sane import if gcsfs is missing
    GCSHttpError = Exception

try:
    from gcsfs.utils import RateLimitException as GCSRateLimitException
except ImportError:
    # Fall back to GCSHttpError when using older library
    GCSRateLimitException = GCSHttpError

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class PapermillIO(object):
    '''
    The holder which houses any io system registered with the system.
    This object is used in a singleton manner to save and load particular
    named Handler objects for reference externally.
    '''

    def __init__(self):
        self.reset()

    def read(self, path, extensions=['.ipynb', '.json']):
        if not fnmatch.fnmatch(os.path.basename(path), '*.*'):
            warnings.warn(
                "the file is not specified with any extension : " + os.path.basename(path)
            )
        elif not any(fnmatch.fnmatch(os.path.basename(path), '*' + ext) for ext in extensions):
            warnings.warn(
                "The specified input file ({}) does not end in one of {}".format(path, extensions)
            )
        # Handle https://github.com/nteract/papermill/issues/317
        notebook_metadata = self.get_handler(path).read(path)
        if isinstance(notebook_metadata, (bytes, bytearray)):
            return notebook_metadata.decode('utf-8')
        return notebook_metadata

    def write(self, buf, path, extensions=['.ipynb', '.json']):
        # Usually no return object here
        if not fnmatch.fnmatch(os.path.basename(path), '*.*'):
            warnings.warn(
                "the file is not specified with any extension : " + os.path.basename(path)
            )
        elif not any(fnmatch.fnmatch(os.path.basename(path), '*' + ext) for ext in extensions):
            warnings.warn(
                "The specified input file ({}) does not end in one of {}".format(path, extensions)
            )
        return self.get_handler(path).write(buf, path)

    def listdir(self, path):
        return self.get_handler(path).listdir(path)

    def pretty_path(self, path):
        return self.get_handler(path).pretty_path(path)

    def reset(self):
        self._handlers = []

    def register(self, scheme, handler):
        # Keep these ordered as LIFO
        self._handlers.insert(0, (scheme, handler))

    def register_entry_points(self):
        # Load handlers provided by other packages
        for entrypoint in entrypoints.get_group_all("papermill.io"):
            self.register(entrypoint.name, entrypoint.load())

    def get_handler(self, path):
        local_handler = None
        for scheme, handler in self._handlers:
            if scheme == 'local':
                local_handler = handler

            if path.startswith(scheme):
                return handler

        if local_handler is None:
            raise PapermillException(
                "Could not find a registered schema handler for: {}".format(path)
            )

        return local_handler


class HttpHandler(object):
    @classmethod
    def read(cls, path):
        return requests.get(path, headers={'Accept': 'application/json'}).text

    @classmethod
    def listdir(cls, path):
        raise PapermillException('listdir is not supported by HttpHandler')

    @classmethod
    def write(cls, buf, path):
        result = requests.put(path, json=json.loads(buf))
        result.raise_for_status()

    @classmethod
    def pretty_path(cls, path):
        return path


class LocalHandler(object):
    def __init__(self):
        self._cwd = None

    def read(self, path):
        with chdir(self._cwd):
            with io.open(path, 'r', encoding="utf-8") as f:
                return f.read()

    def listdir(self, path):
        with chdir(self._cwd):
            return [os.path.join(path, fn) for fn in os.listdir(path)]

    def write(self, buf, path):
        with chdir(self._cwd):
            dirname = os.path.dirname(path)
            if dirname and not os.path.exists(dirname):
                raise FileNotFoundError("output folder {} doesn't exist.".format(dirname))
            with io.open(path, 'w', encoding="utf-8") as f:
                f.write(buf)

    def pretty_path(self, path):
        return path

    def cwd(self, new_path):
        '''Sets the cwd during reads and writes'''
        old_cwd = self._cwd
        self._cwd = new_path
        return old_cwd


class S3Handler(object):
    @classmethod
    def read(cls, path):
        return "\n".join(S3().read(path))

    @classmethod
    def listdir(cls, path):
        return S3().listdir(path)

    @classmethod
    def write(cls, buf, path):
        return S3().cp_string(buf, path)

    @classmethod
    def pretty_path(cls, path):
        return path


class ADLHandler(object):
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = ADL()
        return self._client

    def read(self, path):
        lines = self._get_client().read(path)
        return "\n".join(lines)

    def listdir(self, path):
        return self._get_client().listdir(path)

    def write(self, buf, path):
        return self._get_client().write(buf, path)

    def pretty_path(self, path):
        return path


class ABSHandler(object):
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = AzureBlobStore()
        return self._client

    def read(self, path):
        lines = self._get_client().read(path)
        return "\n".join(lines)

    def listdir(self, path):
        return self._get_client().listdir(path)

    def write(self, buf, path):
        return self._get_client().write(buf, path)

    def pretty_path(self, path):
        return path


class GCSHandler(object):
    RATE_LIMIT_RETRIES = 3
    RETRY_DELAY = 1
    RETRY_MULTIPLIER = 1
    RETRY_MAX_DELAY = 4

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = GCSFileSystem()
        return self._client

    def read(self, path):
        with self._get_client().open(path) as f:
            return f.read()

    def listdir(self, path):
        return self._get_client().ls(path)

    def write(self, buf, path):
        # Wrapped so we can mock retry options during testing
        @retry(
            retry=retry_if_exception_type(PapermillRateLimitException),
            stop=stop_after_attempt(self.RATE_LIMIT_RETRIES),
            wait=wait_exponential(
                multiplier=self.RETRY_MULTIPLIER, min=self.RETRY_DELAY, max=self.RETRY_MAX_DELAY
            ),
            reraise=True,
        )
        def retry_write():
            try:
                with self._get_client().open(path, 'w') as f:
                    return f.write(buf)
            except (GCSHttpError, GCSRateLimitException) as e:
                try:
                    # If code is assigned but unknown, optimistically retry
                    if e.code is None or e.code == 429:
                        raise PapermillRateLimitException(e.message)
                except AttributeError:
                    try:
                        message = e.message
                    except AttributeError:
                        message = "Generic exception {} raised, retrying".format(type(e))
                    raise PapermillRateLimitException(message)
                # Reraise the original exception without retries
                raise

        return retry_write()

    def pretty_path(self, path):
        return path


# Instantiate a PapermillIO instance and register Handlers.
papermill_io = PapermillIO()
papermill_io.register("local", LocalHandler())
papermill_io.register("s3://", S3Handler)
papermill_io.register("adl://", ADLHandler)
papermill_io.register("abs://", ABSHandler())
papermill_io.register("http://", HttpHandler)
papermill_io.register("https://", HttpHandler)
papermill_io.register("gs://", GCSHandler())
papermill_io.register_entry_points()


def read_yaml_file(path):
    """Reads a YAML file from the location specified at 'path'."""
    return yaml.load(papermill_io.read(path, ['.json', '.yaml', '.yml']))


def write_ipynb(nb, path):
    """Saves a notebook object to the specified path.
    Args:
        nb_node (nbformat.NotebookNode): Notebook object to save.
        notebook_path (str): Path to save the notebook object to.
    """
    papermill_io.write(nbformat.writes(nb), path)


def load_notebook_node(notebook_path):
    """Returns a notebook object with papermill metadata loaded from the specified path.

    Args:
        notebook_path (str): Path to the notebook file.

    Returns:
        nbformat.NotebookNode

    """
    nb = nbformat.reads(papermill_io.read(notebook_path), as_version=4)

    if not hasattr(nb.metadata, 'papermill'):
        nb.metadata['papermill'] = {
            'parameters': dict(),
            'environment_variables': dict(),
            'version': __version__,
        }

    for cell in nb.cells:
        if not hasattr(cell.metadata, 'tags'):
            cell.metadata['tags'] = []  # Create tags attr if one doesn't exist.

        if not hasattr(cell.metadata, 'papermill'):
            cell.metadata['papermill'] = dict()
    return nb


def list_notebook_files(path):
    """Returns a list of all the notebook files in a directory."""
    return [p for p in papermill_io.listdir(path) if p.endswith('.ipynb')]


def get_pretty_path(path):
    return papermill_io.pretty_path(path)


@contextmanager
def local_file_io_cwd(path=None):
    try:
        local_handler = papermill_io.get_handler("local")
    except PapermillException:
        logger.warning("No local file handler detected")
    else:
        try:
            old_cwd = local_handler.cwd(path or os.getcwd())
        except AttributeError:
            logger.warning("Local file handler does not support cwd assignment")
        else:
            try:
                yield
            finally:
                local_handler.cwd(old_cwd)
