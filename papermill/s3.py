# -*- coding: utf-8 -*-
"""Utilities for working with S3."""

import os

import logging
import threading
import zlib

from boto3.session import Session

from .exceptions import AwsError
from .utils import retry


logger = logging.getLogger('papermill.s3')


class Bucket(object):
    """
    Represents a Bucket of storage on S3

    Parameters
    ----------
    name : string
        name of the bucket
    service : string, optional (Default is None)
        name of a service resource, such as SQS, EC2, etc.

    """

    def __init__(self, name, service=None):
        self.name = name
        self.service = service

    def list(self, prefix='', delimiter=None):
        """Limits a list of Bucket's objects based on prefix and delimiter."""
        return self.service._list(
            bucket=self.name, prefix=prefix, delimiter=delimiter, objects=True
        )


class Prefix(object):
    """
    Represents a prefix used in an S3 Bucket.

    Parameters
    ----------
    bucket : object
        A bucket of S3 storage
    name : string
        name of the bucket
    service : string, optional (Default is None)
        name of a service resource, such as SQS, EC2, etc.

    """

    def __init__(self, bucket, name, service=None):
        self.bucket = Bucket(bucket, service=service)
        self.name = name
        self.is_prefix = True
        self.service = service

    def __str__(self):
        return 's3://{}/{}'.format(self.bucket.name, self.name)

    def __repr__(self):
        return self.__str__()


class Key(object):
    """
    A key that represents a unique object in an S3 Bucket.

    Represents a file or stream.

    Parameters
    ----------
    bucket : object
        A bucket of S3 storage
    name : string
        representative name of the bucket
    size : ???, optional (Default is None)
    etag : ???, optional (Default is None)
    last_modified : date, optional (Default is None)
    storage_class : ???, optional (Default is None)
    service : string, optional (Default is None)
        name of a service resource, such as SQS, EC2, etc.

    """

    # TODO make size, etag, etc properties that can be called from the
    # object as needed
    def __init__(
        self,
        bucket,
        name,
        size=None,
        etag=None,
        last_modified=None,
        storage_class=None,
        service=None,
    ):
        self.bucket = Bucket(bucket, service=service)
        self.name = name
        self.size = size
        self.etag = etag
        if last_modified:
            try:
                self.last_modified = last_modified.isoformat().split('+')[0] + '.000Z'
            except ValueError:
                self.last_modified = last_modified
        self.storage_class = storage_class
        self.is_prefix = False
        self.service = service

    def __str__(self):
        return 's3://{}/{}'.format(self.bucket.name, self.name)

    def __repr__(self):
        return self.__str__()


class S3(object):
    """
    Wraps S3.

    Parameters
    ----------
    keyname : TODO

    Methods
    -------
    The following are wrapped utilities for S3:
        - cat
        - cp_string
        - list
        - list_dir
        - read

    """

    s3_session = (None, None, None)
    lock = threading.RLock()

    def __init__(self, keyname=None, *args, **kwargs):
        with self.lock:
            if not all(S3.s3_session):
                session = Session()
                client = session.client('s3')

                session_params = {}
                endpoint_url = os.environ.get('BOTO3_ENDPOINT_URL', None)
                if endpoint_url:
                    session_params['endpoint_url'] = endpoint_url

                s3 = session.resource('s3', **session_params)
                S3.s3_session = (session, client, s3)

        (self.session, self.client, self.s3) = S3.s3_session

    def _bucket_name(self, bucket):
        return self._clean(bucket).split('/', 1)[0]

    def _clean(self, name):
        if name.startswith('s3n:'):
            name = 's3:' + name[4:]
        if self._is_s3(name):
            return name[5:]
        return name

    def _clean_s3(self, name):
        return 's3:' + name[4:] if name.startswith('s3n:') else name

    def _get_key(self, name):
        if isinstance(name, Key):
            return name

        return Key(bucket=self._bucket_name(name), name=self._key_name(name), service=self)

    def _key_name(self, name):
        cleaned = self._clean(name).split('/', 1)
        return cleaned[1] if len(cleaned) > 1 else None

    @retry(3)
    def _list(
        self,
        prefix='',
        bucket=None,
        delimiter=None,
        keys=False,
        objects=False,
        page_size=1000,
        **kwargs
    ):
        assert bucket is not None, 'You must specify a bucket to list'

        bucket = self._bucket_name(bucket)
        paginator = self.client.get_paginator('list_objects_v2')
        operation_parameters = {
            'Bucket': bucket,
            'Prefix': prefix,
            'PaginationConfig': {'PageSize': page_size},
        }
        if delimiter:
            operation_parameters['Delimiter'] = delimiter

        page_iterator = paginator.paginate(**operation_parameters)

        def sort(item):
            if 'Key' in item:
                return item['Key']
            return item['Prefix']

        for page in page_iterator:
            locations = sorted(
                [i for i in page.get('Contents', []) + page.get('CommonPrefixes', [])], key=sort
            )

            for item in locations:
                if objects or keys:
                    if 'Key' in item:
                        yield Key(
                            bucket,
                            item['Key'],
                            size=item.get('Size'),
                            etag=item.get('ETag'),
                            last_modified=item.get('LastModified'),
                            storage_class=item.get('StorageClass'),
                            service=self,
                        )
                    elif objects:
                        yield Prefix(bucket, item['Prefix'], service=self)
                else:
                    prefix = item['Key'] if 'Key' in item else item['Prefix']
                    yield 's3://{}/{}'.format(bucket, prefix)

    def _put(self, source, dest, num_callbacks=10, policy='bucket-owner-full-control', **kwargs):
        key = self._get_key(dest)
        obj = self.s3.Object(key.bucket.name, key.name)

        # support passing in open file obj.  Why did we do this in the past?

        if not isinstance(source, str):
            obj.upload_fileobj(source, ExtraArgs={'ACL': policy})
        else:
            obj.upload_file(source, ExtraArgs={'ACL': policy})
        return key

    def _put_string(
        self, source, dest, num_callbacks=10, policy='bucket-owner-full-control', **kwargs
    ):
        key = self._get_key(dest)
        obj = self.s3.Object(key.bucket.name, key.name)

        if isinstance(source, str):
            source = source.encode('utf-8')
        obj.put(Body=source, ACL=policy)
        return key

    def _is_s3(self, name):
        # only allow file objects from local
        if not isinstance(name, (str, Key, Prefix)):
            return False

        name = self._clean_s3(name)
        return 's3://' in name

    def cat(
        self,
        source,
        buffersize=None,
        memsize=2 ** 24,
        compressed=False,
        encoding='UTF-8',
        raw=False,
    ):
        """
        Returns an iterator for the data in the key or nothing if the key
        doesn't exist. Decompresses data on the fly (if compressed is True
        or key ends with .gz) unless raw is True. Pass None for encoding to
        skip encoding.

        """
        assert self._is_s3(source) or isinstance(source, Key), 'source must be a valid s3 path'

        key = self._get_key(source) if not isinstance(source, Key) else source
        compressed = (compressed or key.name.endswith('.gz')) and not raw
        if compressed:
            decompress = zlib.decompressobj(16 + zlib.MAX_WBITS)

        size = 0
        bytes_read = 0
        err = None
        undecoded = ''
        if key:
            # try to read the file multiple times
            for i in range(100):
                obj = self.s3.Object(key.bucket.name, key.name)
                buffersize = buffersize if buffersize is not None else 2 ** 20

                if not size:
                    size = obj.content_length
                elif size != obj.content_length:
                    raise AwsError('key size unexpectedly changed while reading')

                r = obj.get(Range="bytes={}-".format(bytes_read))

                try:
                    while bytes_read < size:
                        # this making this weird check because this call is
                        # about 100 times slower if the amt is too high
                        if size - bytes_read > buffersize:
                            bytes = r['Body'].read(amt=buffersize)
                        else:
                            bytes = r['Body'].read()
                        if compressed:
                            s = decompress.decompress(bytes)
                        else:
                            s = bytes

                        if encoding and not raw:
                            try:
                                decoded = undecoded + s.decode(encoding)
                                undecoded = ''
                                yield decoded
                            except UnicodeDecodeError:
                                undecoded += s
                                if len(undecoded) > memsize:
                                    raise
                        else:
                            yield s

                        bytes_read += len(bytes)

                except zlib.error:
                    logger.error("Error while decompressing [%s]", key.name)
                    raise
                except UnicodeDecodeError:
                    raise
                except Exception:
                    err = True
                    pass

                if size <= bytes_read:
                    break

            if size != bytes_read:
                if err:
                    raise Exception
                else:
                    raise AwsError('Failed to fully read [%s]' % source.name)

            if undecoded:
                assert encoding is not None  # only time undecoded is set

                # allow exception to be raised if one is thrown
                decoded = undecoded.decode(encoding)
                yield decoded

    def cp_string(self, source, dest, **kwargs):
        """
        Copies source string into the destination location.

        Parameters
        ----------
        source: string
            the string with the content to copy
        dest: string
            the s3 location
        """

        assert isinstance(source, str), "source must be a string"
        assert self._is_s3(dest), "Destination must be s3 location"

        return self._put_string(source, dest, **kwargs)

    def list(self, name, iterator=False, **kwargs):
        """
        Returns a list of the files under the specified path
        name must be in the form of `s3://bucket/prefix`

        Parameters
        ----------
        keys: optional
           if True then this will return the actual boto keys for files
           that are encountered
        objects: optional
           if True then this will return the actual boto objects for
           files or prefixes that are encountered
        delimiter: optional
           if set this
        iterator: optional
           if True return iterator rather than converting to list object

        """
        assert self._is_s3(name), "name must be in form s3://bucket/key"

        it = self._list(bucket=self._bucket_name(name), prefix=self._key_name(name), **kwargs)
        return iter(it) if iterator else list(it)

    def listdir(self, name, **kwargs):
        """
        Returns a list of the files under the specified path.

        This is different from list as it will only give you files under the
        current directory, much like ls.

        name must be in the form of `s3://bucket/prefix/`

        Parameters
        ----------
        keys: optional
            if True then this will return the actual boto keys for files
            that are encountered
        objects: optional
            if True then this will return the actual boto objects for
            files or prefixes that are encountered

        """
        assert self._is_s3(name), "name must be in form s3://bucket/prefix/"

        if not name.endswith('/'):
            name += "/"
        return self.list(name, delimiter='/', **kwargs)

    def read(self, source, compressed=False, encoding='UTF-8'):
        """
        Iterates over a file in s3 split on newline.

        Yields a line in file.

        """
        buf = ''
        for block in self.cat(source, compressed=compressed, encoding=encoding):
            buf += block
            if '\n' in buf:
                ret, buf = buf.rsplit('\n', 1)
                for line in ret.split('\n'):
                    yield line

        lines = buf.split('\n')
        for line in lines[:-1]:
            yield line

        # only yield the last line if the line has content in it
        if lines[-1]:
            yield lines[-1]
