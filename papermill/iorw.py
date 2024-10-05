import fnmatch
import json
import os
import sys
import warnings
from contextlib import contextmanager

import entrypoints
import nbformat
import requests
import yaml
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .exceptions import (
    PapermillException,
    PapermillRateLimitException,
    missing_dependency_generator,
    missing_environment_variable_generator,
)
from .log import logger
from .utils import chdir
from .version import version as __version__

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

try:
    from pyarrow.fs import FileSelector, HadoopFileSystem
except ImportError:
    HadoopFileSystem = missing_dependency_generator("pyarrow", "hdfs")

try:
    from github import Github
except ImportError:
    Github = missing_dependency_generator("pygithub", "github")


def fallback_gs_is_retriable(e):
    try:
        print(e.code)
        return e.code is None or e.code == 429
    except AttributeError:
        print(e)
        return False


try:
    try:
        # Default to gcsfs library's retry logic
        from gcsfs.retry import is_retriable as gs_is_retriable
    except ImportError:
        from gcsfs.utils import is_retriable as gs_is_retriable
except ImportError:
    gs_is_retriable = fallback_gs_is_retriable

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class PapermillIO:
    '''
    The holder which houses any io system registered with the system.
    This object is used in a singleton manner to save and load particular
    named Handler objects for reference externally.
    '''

    def __init__(self):
        self.reset()

    def read(self, path, extensions=['.ipynb', '.json']):
        # Handle https://github.com/nteract/papermill/issues/317
        notebook_metadata = self.get_handler(path, extensions).read(path)
        if isinstance(notebook_metadata, (bytes, bytearray)):
            return notebook_metadata.decode('utf-8')
        return notebook_metadata

    def write(self, buf, path, extensions=['.ipynb', '.json']):
        return self.get_handler(path, extensions).write(buf, path)

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

    def get_handler(self, path, extensions=None):
        '''Get I/O Handler based on a notebook path

        Parameters
        ----------
        path : str or nbformat.NotebookNode or None
        extensions : list of str, optional
            Required file extension options for the path (if path is a string), which
            will log a warning if there is no match. Defaults to None, which does not
            check for any extensions

        Raises
        ------
        PapermillException: If a valid I/O handler could not be found for the input path

        Returns
        -------
        I/O Handler
        '''
        if path is None:
            return NoIOHandler()

        if isinstance(path, nbformat.NotebookNode):
            return NotebookNodeHandler()

        if extensions:
            if not fnmatch.fnmatch(os.path.basename(path).split('?')[0], '*.*'):
                warnings.warn(f"the file is not specified with any extension : {os.path.basename(path)}")
            elif not any(fnmatch.fnmatch(os.path.basename(path).split('?')[0], f"*{ext}") for ext in extensions):
                warnings.warn(f"The specified file ({path}) does not end in one of {extensions}")

        local_handler = None
        for scheme, handler in self._handlers:
            if scheme == 'local':
                local_handler = handler

            if path.startswith(scheme):
                return handler

        if local_handler is None:
            raise PapermillException(f"Could not find a registered schema handler for: {path}")

        return local_handler


class HttpHandler:
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


class LocalHandler:
    def __init__(self):
        self._cwd = None

    def read(self, path):
        try:
            with chdir(self._cwd):
                with open(path, encoding="utf-8") as f:
                    return f.read()
        except OSError as e:
            try:
                # Check if path could be a notebook passed in as a
                # string
                json.loads(path)
                return path
            except ValueError:
                # Propagate the IOError
                raise e

    def listdir(self, path):
        with chdir(self._cwd):
            return [os.path.join(path, fn) for fn in os.listdir(path)]

    def write(self, buf, path):
        with chdir(self._cwd):
            dirname = os.path.dirname(path)
            if dirname and not os.path.exists(dirname):
                raise FileNotFoundError(f"output folder {dirname} doesn't exist.")
            with open(path, 'w', encoding="utf-8") as f:
                f.write(buf)

    def pretty_path(self, path):
        return path

    def cwd(self, new_path):
        '''Sets the cwd during reads and writes'''
        old_cwd = self._cwd
        self._cwd = new_path
        return old_cwd


class S3Handler:
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


class ADLHandler:
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


class ABSHandler:
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


class GCSHandler:
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
            wait=wait_exponential(multiplier=self.RETRY_MULTIPLIER, min=self.RETRY_DELAY, max=self.RETRY_MAX_DELAY),
            reraise=True,
        )
        def retry_write():
            try:
                with self._get_client().open(path, 'w') as f:
                    return f.write(buf)
            except Exception as e:
                try:
                    message = e.message
                except AttributeError:
                    message = f"Generic exception {type(e)} raised"
                if gs_is_retriable(e):
                    raise PapermillRateLimitException(message)
                # Reraise the original exception without retries
                raise

        return retry_write()

    def pretty_path(self, path):
        return path


class HDFSHandler:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = HadoopFileSystem(host="default")
        return self._client

    def read(self, path):
        with self._get_client().open_input_stream(path) as f:
            return f.read()

    def listdir(self, path):
        return [f.path for f in self._get_client().get_file_info(FileSelector(path))]

    def write(self, buf, path):
        with self._get_client().open_output_stream(path) as f:
            return f.write(str.encode(buf))

    def pretty_path(self, path):
        return path


class GithubHandler:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            token = os.environ.get('GITHUB_ACCESS_TOKEN', None)
            if token:
                self._client = Github(token)
            else:
                self._client = Github()
        return self._client

    def read(self, path):
        splits = path.split('/')
        org_id = splits[3]
        repo_id = splits[4]
        ref_id = splits[6]
        sub_path = '/'.join(splits[7:])
        repo = self._get_client().get_repo(f"{org_id}/{repo_id}")
        content = repo.get_contents(sub_path, ref=ref_id)
        return content.decoded_content

    def listdir(self, path):
        raise PapermillException('listdir is not supported by GithubHandler')

    def write(self, buf, path):
        raise PapermillException('write is not supported by GithubHandler')

    def pretty_path(self, path):
        return path


class StreamHandler:
    '''Handler for Stdin/Stdout streams'''

    def read(self, path):
        return sys.stdin.read()

    def listdir(self, path):
        raise PapermillException('listdir is not supported by Stream Handler')

    def write(self, buf, path):
        try:
            return sys.stdout.buffer.write(buf.encode('utf-8'))
        except AttributeError:
            # Originally required by https://github.com/nteract/papermill/issues/420
            # Support Buffer.io objects
            return sys.stdout.write(buf.encode('utf-8'))

    def pretty_path(self, path):
        return path


class NotebookNodeHandler:
    '''Handler for input_path of nbformat.NotebookNode object'''

    def read(self, path):
        return nbformat.writes(path)

    def listdir(self, path):
        raise PapermillException('listdir is not supported by NotebookNode Handler')

    def write(self, buf, path):
        raise PapermillException('write is not supported by NotebookNode Handler')

    def pretty_path(self, path):
        return 'NotebookNode object'


class NoIOHandler:
    '''Handler for output_path of None - intended to not write anything'''

    def read(self, path):
        raise PapermillException('read is not supported by NoIOHandler')

    def listdir(self, path):
        raise PapermillException('listdir is not supported by NoIOHandler')

    def write(self, buf, path):
        return

    def pretty_path(self, path):
        return 'Notebook will not be saved'


# Hack to make YAML loader not auto-convert datetimes
# https://stackoverflow.com/a/52312810
class NoDatesSafeLoader(yaml.SafeLoader):
    yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != 'tag:yaml.org,2002:timestamp']
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


# Instantiate a PapermillIO instance and register Handlers.
papermill_io = PapermillIO()
papermill_io.register("local", LocalHandler())
papermill_io.register("s3://", S3Handler)
papermill_io.register("adl://", ADLHandler())
papermill_io.register("abs://", ABSHandler())
papermill_io.register("http://", HttpHandler)
papermill_io.register("https://", HttpHandler)
papermill_io.register("gs://", GCSHandler())
papermill_io.register("hdfs://", HDFSHandler())
papermill_io.register("http://github.com/", GithubHandler())
papermill_io.register("https://github.com/", GithubHandler())
papermill_io.register("-", StreamHandler())
papermill_io.register_entry_points()


def read_yaml_file(path):
    """Reads a YAML file from the location specified at 'path'."""
    return yaml.load(papermill_io.read(path, ['.json', '.yaml', '.yml']), Loader=NoDatesSafeLoader)


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
    nb_upgraded = nbformat.v4.upgrade(nb)
    if nb_upgraded is not None:
        nb = nb_upgraded

    if not hasattr(nb.metadata, 'papermill'):
        nb.metadata['papermill'] = {
            'default_parameters': dict(),
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
