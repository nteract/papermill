# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from ansiwrap import strip_color


class AwsError(Exception):
    """Raised when an AWS Exception is encountered."""


class FileExistsError(AwsError):
    """Raised when a File already exists on S3."""


class PapermillException(Exception):
    """Raised when an exception is encountered when operating on a notebook."""


class PapermillExecutionError(PapermillException):
    """Raised when an exception is encountered in a notebook."""

    def __init__(self, exec_count, source, ename, evalue, traceback):
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
