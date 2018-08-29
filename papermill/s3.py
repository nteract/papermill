# -*- coding: utf-8 -*-
"""Utilities for working with S3."""
from __future__ import unicode_literals
from past.builtins import basestring, str

from concurrent import futures
import fnmatch
from functools import wraps, reduce
import gzip
import itertools
import logging
import os
import re
import shutil
import tempfile
import threading
import zlib


import boto3
from boto3.session import Session

import six

from .exceptions import AwsError, FileExistsError


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
        return str(self)


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
        return str(self)


# retry decorator
def retry(num):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(num):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.debug('retrying: {}'.format(e))
            else:
                raise Exception  # TODO verify what to raise

        return wrapper

    return decorate


class S3(object):
    """
    Wraps S3.

    Parameters
    ----------
    keyname : TODO
    use_akms : bool, optional (Default is None) (TODO What is akms? Kinesis?)
    host : DEPRECATED. string, optional (Default is None)
    region : string, optional (Default is 'us-east-1')

    Methods
    -------
    The following are wrapped utilities for S3:
        - cat
        - catdir (TODO refactor to cat_dir)
        - cp
        - cpdir (TODO cp_dir)
        - cpmerge (TODO cp_merge)
        - cp_string
        - get_key
        - list
        - list_buckets
        - list_dir
        - list_dir_iterator
        - list_glob
        - list_globs
        - new_folder
        - readdir (TODO read_dir)
        - read
        - rm
        - rmdir (TODO rm_dir)

    """

    sessions = {}
    lock = threading.RLock()

    # TODO: add support for assume role.

    def __init__(self, keyname=None, use_akms=None, host=None, region='us-east-1', *args, **kwargs):

        import botocore.session

        # DEPRECATED - `host`
        if host:
            logger.warning('the host param is deprecated')

        use_akms = use_akms if use_akms is not None else 'USE_AKMS' in os.environ

        args = (keyname, use_akms)
        with self.lock:
            if args not in self.sessions:
                session = Session(
                    botocore_session=botocore.session.Session(
                        session_vars={'akms_keyname': keyname, 'use_akms': use_akms}
                    )
                )
                client = session.client('s3')
                s3 = session.resource('s3')
                self.sessions[args] = (session, client, s3)

        (self.session, self.client, self.s3) = self.sessions[args]

    def __batches(self, it, size=1000):
        while True:
            data = itertools.islice(it, size)
            batch = list(data)
            if not batch:
                break
            yield batch

    def __create_callback(self, filename, total=None, callback=None):
        if callback is None:
            cur = 0  # noqa TODO refactor cur name

            class Callback(object):
                def __init__(self, total):
                    self.cur = 0
                    self.total = total

                def __call__(self, retr):

                    if self.total:
                        self.cur += retr  # TODO refactor cur and retr names
                        logger.debug(
                            '%s: %6d/%dkb (%3.2f%% Complete)' % filename,
                            self.cur / 1024,
                            self.total / 1024,
                            self.cur / float(total) * 100,
                        )

        return callback

    def _bucket(self, bucket):
        if isinstance(bucket, Key):
            return bucket.bucket
        return Bucket(self._bucket_name(bucket), service=self)

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

    @retry(3)
    def _copy(self, source, dest):
        key = self._get_key(dest)
        source_key = self._get_key(source)
        obj = self.s3.Object(key.bucket.name, key.name)
        obj.copy_from(CopySource='{}/{}'.format(source_key.bucket.name, source_key.name))
        return key

    @retry(3)
    def _get(self, source, dest=None, num_callbacks=10, **kwargs):
        assert dest is not None, 'a destination must be provided'

        targetFile = isinstance(dest, six.string_types)
        if targetFile:
            tmpfile = tempfile.NamedTemporaryFile()
        else:
            tmpfile = dest

        try:
            key = self._get_key(source)
            obj = self.s3.Object(key.bucket.name, key.name)
            obj.load()
            obj.download_fileobj(
                tmpfile,
                Callback=self.__create_callback(
                    source, total=obj.content_length, callback=kwargs.get('callback')
                ),
            )
            if targetFile:
                tmpfile.seek(0)
                shutil.copyfileobj(tmpfile, open(dest, 'wb'))
            return key
        finally:
            if targetFile:
                tmpfile.close()

    def _get_key(self, name):
        if isinstance(name, Key):
            return name

        return Key(bucket=self._bucket_name(name), name=self._key_name(name), service=self)

    def _get_file_obj(self, f, mode='wb'):
        return gzip.open(f, mode) if f.endswith('.gz') else open(f, mode)

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
        length = 0

        # support passing in open file obj.  Why did we do this in the past?

        if not isinstance(source, six.string_types):
            obj.upload_fileobj(
                source,
                ExtraArgs={'ACL': policy},
                Callback=self.__create_callback(
                    dest, total=os.fstat(source.fileno()).st_size, callback=kwargs.get('callback')
                ),
            )
        else:
            obj.upload_file(
                source,
                ExtraArgs={'ACL': policy},
                Callback=self.__create_callback(
                    dest, total=length, callback=kwargs.get('callback')
                ),
            )
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
        if not isinstance(name, (basestring, Key, Prefix)):
            return False

        name = self._clean_s3(name)
        return 's3://' in name

    def _sizeof(self, key, bucket=None):
        assert bucket is not None, 'You must specify a bucket'

        response = self.client.head_object(Bucket=bucket, Key=key)
        return response['ContentLength']

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

    def catdir(self, source, buffersize=None, compressed=False, encoding='UTF-8'):
        """
        Iterates over a dir in s3 split on newline.

        Yields chunks of data from the file.

        """
        for f in self.listdir(source, keys=True):
            logger.debug('S3.catdir: %s', f)
            full_name = 's3://{}/{}'.format(f.bucket.name, f.name)
            for l in self.cat(
                full_name, buffersize=buffersize, compressed=compressed, encoding=encoding
            ):
                yield l

    def cp(self, source, dest, **kwargs):
        """
        Copies to and from an s3 bucket to a file.

        The source and destination should be the fully qualified path of an
        s3 key and the filename to copy from/to.

        """
        fr = self._is_s3(source)
        to = self._is_s3(dest)
        if fr and to:
            return self._copy(source, dest, **kwargs)
        elif fr:
            return self._get(source, dest, **kwargs)
        else:
            return self._put(source, dest, **kwargs)

    def cpdir(self, source, dest, recursive=True, **kwargs):
        """
        Copies to and from an s3 prefix to a directory.  The source and
        destination should be the fully qualified path of an s3 prefix and the
        directory to copy from/to.

        """
        source = source.endswith('/') and source or "%s/" % source
        source = self._clean_s3(source)
        dest = re.sub('/$', '', dest)

        fr = self._is_s3(source)
        to = self._is_s3(dest)

        if fr:
            for i in list(self.listdir(source)):
                file = "%s/%s" % (dest, i.replace(source, ''))
                if not i.endswith('/'):
                    self.cp(i, file, **kwargs)
                elif recursive:
                    if not to and not os.path.exists(file):
                        os.makedirs(file)
                    self.cpdir(i, file, recursive=recursive, **kwargs)
        else:
            for i in os.listdir(source):
                s = "%s/%s" % (source, i)
                d = "%s/%s" % (dest, i)
                if recursive and os.path.isdir(s):
                    self.cpdir(s, d, recursive=recursive, **kwargs)
                else:
                    self._put(s, d, **kwargs)

    def cpmerge(self, source, dest):
        """
        Takes a source directory and a destination file as input and
        concatenates files in src into the destination local file.

        """
        fr = self._is_s3(source)
        to = self._is_s3(dest)

        if fr and not to:
            if os.path.isfile(dest):
                raise FileExistsError("File {} already exists".format(dest))
            if os.path.isdir(dest):
                raise AwsError("Destination {} is a directory".format(dest))

            try:
                os.makedirs(os.path.dirname(dest))
            except (OSError) as e:
                if e.strerror != 'File exists':
                    raise

            with self._get_file_obj(dest) as outfile:
                for f in self.listdir(source):
                    logger.debug('reading {}'.format(f))
                    for line in self.cat(f, compressed=f.endswith('gz')):
                        outfile.write(line)
        else:
            raise AwsError("Copy-merging {} to {} is not supported".format(source, dest))

    def cp_string(self, source, dest, **kwargs):
        """
        Copies source string into the destination location.

        Parameters
        ----------
        source: string
            the string with the content to copy
        dest: string
            the s3 location

        Uses basestring type (python2) when checking if a string

        """

        assert isinstance(source, basestring), "source must be a string"
        assert self._is_s3(dest), "Destination must be s3 location"

        return self._put_string(source, dest, **kwargs)

    def get_key(self, name):
        """
        Get Key object if the name represents a key, otherwise return None.

        Examples:

        >>> s3.get_key('s3://netflix-dataoven-test-users/jwalton/nothing.py')

            <Key: netflix-dataoven-test-users,jwalton/nothing.py>

        >>> s3.get_key('s3://netflix-dataoven-test-users/jwalton/')

            None

        Args:
           name (str): the full s3 location for which to get the key

        Returns:
           A boto3.resources.factory.s3.Object object if the name represents
           a file or None if the name is a prefix

        """
        assert self._is_s3(name), "location must be in form s3://bucket/key"

        key = self._get_key(name)
        try:
            obj = self.s3.Object(key.bucket.name, key.name)
            obj.load()
            return obj
        except boto3.exceptions.botocore.exceptions.ClientError as e:
            logger.debug(e)
            pass

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

    def list_buckets(self):
        return [bucket['Name'] for bucket in self.client.list_buckets().get('Buckets', [])]

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

    def listdir_iterator(self, name):
        """
        Iterates over a list of objects in a bucket.

        Calls `bucket.list` which returns a
        `boto.s3.bucketlistresultset.bucketlistresultset`

        Items returned from iterator are `boto` `objects`.

        """
        assert self._is_s3(name), "name must be in form s3://bucket/key"

        return self._list(
            prefix=self._key_name(name), bucket=self._bucket_name(name), objects=True, delimiter='/'
        )

    def listglob(self, glb, **kwargs):
        """
        Returns a list of the files matching a glob.

        Name must be in the form of s3://bucket/glob

        """
        r = []
        regex = re.compile('[*?\[]')
        for file in self.list(regex.split(glb, 1)[0], **kwargs):
            if fnmatch.fnmatch(str(file), glb):
                r.append(file)
        return r

    def listglobs(self, *args, **kwargs):
        """
        Returns a list of files for multiple glob operators.

        Equivalent to list(listglob(args[0])) + list(listglob(args[1]))  + ...

        Use Python lambda and reduce

        arguments acc and x
        sequence acc + x
        executor.map(self.listglob, args)
        []

        The function reduce(func, seq) continually applies the function
        func() to the sequence seq. It returns a single value.

        """
        with futures.ThreadPoolExecutor(max_workers=kwargs.get('threads', len(args))) as executor:
            out = reduce(lambda acc, x: acc + x, executor.map(self.listglob, args), [])
        return out

    def new_folder(self, name):
        """
        Creates a new "folder" by adding a file called "_empty" under the prefix given.

        Example:
            >>> s3.new_folder('s3://thebucket/somedir/newdir/')

        Args:
            name - the full location for the new "folder" in the format s3://bucket/prefix

        Returns: key for the new "folder"

        """
        assert self._is_s3(name), "name must be in form s3://bucket/new_key/"

        if not name.endswith("/"):
            name += "/"

        existing = self.get_key(name)
        if existing is not None:
            raise Exception("key {} already exists".format(name))

        loc = name + "_empty"
        self._put_string("", loc)

        return self.get_key(name)

    def readdir(self, source, compressed=False, encoding='UTF-8'):
        """
        Iterates over a dir in s3 split on newline.

        Yields line in file in dir.

        """
        for f in self.listdir(source, keys=True):
            for l in self.read(str(f), compressed=compressed, encoding=encoding):
                yield l

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

    def rm(self, target):
        """
        Remove a single key from s3.

        If you want to remove a directory use rmdir.

        """
        assert self._is_s3(target), 'target must be a valid s3 path'

        key = self._get_key(target)
        if key:
            obj = self.s3.Object(key.bucket.name, key.name)
            return obj.delete()

    def rmdir(self, target, delimiter='/'):
        """Removes every key that falls under the target directory."""
        assert self._is_s3(target), 'target must be a valid s3 path'

        bucket = self.s3.Bucket(self._bucket_name(target))
        errors = []
        for batch in self.__batches(
            self._list(bucket=self._bucket_name(target), prefix=self._key_name(target), keys=True)
        ):
            keys = [dict(Key=n.name) for n in batch]
            response = bucket.delete_objects(Delete={'Objects': keys})
            if 'Errors' in response:
                errors += response['Errors']
        if errors:
            logger.warning("errors deleting: {}".format(errors))


# leaving this here for compatibility
def split(path):
    """
    Splits an s3 path into bucket and prefix, like `os.path.split`.

    It can only be used once.

    For example, `s3://foo/bar/baz` would return `['foo','bar/baz']`

    .. note::
       A trailing `/` is significant in s3, and it will not be stripped,
       ie `s3://foo/bar/baz/` will return `['foo','bar/baz/']`

    """
    if not path.startswith('s3://'):
        raise ValueError('path must start with s3://')
    path = path[5:]
    if path:
        if '/' in path:
            return path.split('/', 1)
        else:
            return [path, '']
    else:
        return ['', '']
