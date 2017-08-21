
class AwsError(Exception):
    """Raised when an AWS Exception is encountered."""


class FileExistsError(AwsError):
    """Raised when a File already exists on S3."""


class PapermillException(Exception):
    """Raised when an exception is encountered when operating on a notebook."""
