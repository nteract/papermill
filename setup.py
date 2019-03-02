#!/usr/bin/env python
# -*- coding: utf-8 -*-
""""
setup.py

Note: Do a version check for IPython.
    IPython v6+ no longer supports Python 2.
    If Python 2, install ipython 5.x.

See:
https://packaging.python.org/tutorials/packaging-projects/
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject

"""
from __future__ import print_function
import os
import sys
from os import path
from setuptools import setup

# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open

local_path = os.path.dirname(__file__)
# Fix for tox which manipulates execution pathing
if not local_path:
    local_path = '.'
here = path.abspath(local_path)


def version():
    with open(here + '/papermill/version.py', 'r') as ver:
        for line in ver.readlines():
            if line.startswith('version ='):
                return line.split(' = ')[-1].strip()[1:-1]
    raise ValueError('No version found in papermill/version.py')


python_2 = sys.version_info[0] == 2


def read(fname):
    with open(fname, 'rU' if python_2 else 'r') as fhandle:
        return fhandle.read()


def read_reqs(fname):
    req_path = os.path.join(here, fname)
    return [req.strip() for req in read(req_path).splitlines() if req.strip()]


s3_reqs = read_reqs('requirements-s3.txt')
azure_reqs = read_reqs('requirements-azure.txt')
gcs_reqs = read_reqs('requirements-gcs.txt')
all_reqs = s3_reqs + azure_reqs + gcs_reqs
dev_reqs = read_reqs('requirements-dev.txt') + all_reqs
extras_require = {
    "test": dev_reqs,
    "dev": dev_reqs,
    "all": all_reqs,
    "s3": s3_reqs,
    "azure": azure_reqs,
    "gcs": gcs_reqs,
}

# Tox has a weird issue where it can't import pip from it's virtualenv when skipping normal installs
if not bool(int(os.environ.get('SKIP_PIP_CHECK', 0))):
    pip_too_old = False
    pip_message = ''
    try:
        import pip

        pip_version = tuple([int(x) for x in pip.__version__.split('.')[:3]])
        pip_too_old = pip_version < (9, 0, 1)
        if pip_too_old:
            # pip is too old to handle IPython deps gracefully
            pip_message = (
                'Your pip version is out of date. Papermill requires pip >= 9.0.1. \n'
                'pip {} detected. Please install pip >= 9.0.1.'.format(pip.__version__)
            )
    except Exception:
        # We only want to optimistically report old versions
        pass

    if pip_message:
        print(pip_message, file=sys.stderr)
        sys.exit(1)


# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='papermill',
    version=version(),
    description='Parametrize and run Jupyter and nteract Notebooks',
    author='nteract contributors',
    author_email='nteract@googlegroups.com',
    license='BSD',
    # Note that this is a string of words separated by whitespace, not a list.
    keywords='jupyter mapreduce nteract pipeline notebook',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/nteract/papermill',
    packages=['papermill'],
    install_requires=read_reqs('requirements.txt'),
    extras_require=extras_require,
    entry_points={'console_scripts': ['papermill = papermill.cli:papermill']},
    project_urls={
        'Documentation': 'https://papermill.readthedocs.io',
        'Funding': 'https://nteract.io',
        'Source': 'https://github.com/nteract/papermill/',
        'Tracker': 'https://github.com/nteract/papermill/issues',
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2.7',
    ],
)
