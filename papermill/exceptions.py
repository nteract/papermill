# -*- coding: utf-8 -*-

from ansiwrap import strip_color


class AwsError(Exception):
    """Raised when an AWS Exception is encountered."""


class FileExistsError(AwsError):
    """Raised when a File already exists on S3."""


class PapermillException(Exception):
    """Raised when an exception is encountered when operating on a notebook."""


class PapermillMissingParameterException(PapermillException):
    """Raised when a parameter without a value is required to operate on a notebook."""


class PapermillExecutionError(PapermillException):
    """Raised when an exception is encountered in a notebook."""

    def __init__(self, cell_index, exec_count, source, ename, evalue, traceback):
        self.cell_index = cell_index
        self.exec_count = exec_count
        self.source = source
        self.ename = ename
        self.evalue = evalue
        self.traceback = traceback
        message = "\n" + 75 * "-" + "\n"
        message += 'Exception encountered at "In [%s]":\n' % str(exec_count)
        message += strip_color("\n".join(traceback))
        message += "\n"

        super(PapermillExecutionError, self).__init__(message)


class PapermillRateLimitException(PapermillException):
    """Raised when an io request has been rate limited"""


class PapermillOptionalDependencyException(PapermillException):
    """Raised when an exception is encountered when an optional plugin is missing."""


class PapermillWarning(Warning):
    """Base warning for papermill."""


class PapermillParameterOverwriteWarning(PapermillWarning):
    """Callee overwrites caller argument to pass down the stream."""


def missing_dependency_generator(package, dep):
    def missing_dep():
        raise PapermillOptionalDependencyException(
            "The {package} optional dependency is missing. "
            "Please run pip install papermill[{dep}] to install this dependency".format(
                package=package, dep=dep
            )
        )

    return missing_dep


def missing_environment_variable_generator(package, env_key):
    def missing_dep():
        raise PapermillOptionalDependencyException(
            "The {package} optional dependency is present, but the environment "
            "variable {env_key} is not set. Please set this variable as "
            "required by {package} on your platform.".format(package=package, env_key=env_key)
        )

    return missing_dep
