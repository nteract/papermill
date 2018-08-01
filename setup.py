#!/usr/bin/env python
# -*- coding: utf-8 -*-
""""
setup.py

Note: Install ipython version based on python version.
      If python 2, install ipython 5.x (python2 is not supported in ipython 6.

"""
from __future__ import print_function
import os
import sys
from os.path import exists
from setuptools import setup

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
    pip_message = 'No pip detected; we were unable to import pip. \n' 'To use papermill, please install pip >= 9.0.1.'
except Exception:
    pass

if pip_message:
    print(pip_message, file=sys.stderr)
    sys.exit(1)


setup(
    name='papermill',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Parametrize and Run Jupyter Notebooks',
    author='nteract contributors',
    author_email='jupyter@googlegroups.com',
    license='BSD',
    keywords="jupyter mapreduce",
    long_description=(open('README.rst').read() if exists('README.rst') else ''),
    url='https://github.com/nteract/papermill',
    packages=['papermill'],
    install_requires=required,
    extras_require=extras_require,
    entry_points={'console_scripts': ['papermill = papermill.cli:papermill']},
)
