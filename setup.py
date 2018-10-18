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

import versioneer

python_2 = sys.version_info[0] == 2


def read(fname):
    with open(fname, 'rU' if python_2 else 'r') as fhandle:
        return fhandle.read()


req_path = os.path.join(os.path.dirname('__file__'), 'requirements.txt')
required = [req.strip() for req in read(req_path).splitlines() if req.strip()]

test_req_path = os.path.join(os.path.dirname('__file__'), 'requirements-dev.txt')
test_required = [req.strip() for req in read(test_req_path).splitlines() if req.strip()]
extras_require = {"test": test_required, "dev": test_required}

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
except ImportError:
    pip_message = (
        'No pip detected; we were unable to import pip. \n'
        'To use papermill, please install pip >= 9.0.1.'
    )
except Exception:
    pass

if pip_message:
    print(pip_message, file=sys.stderr)
    sys.exit(1)


# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='papermill',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
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
    install_requires=required,
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
