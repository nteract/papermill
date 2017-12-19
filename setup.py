#!/usr/bin/env python
# -*- coding: utf-8 -*-
""""
setup.py

Note: Install ipython version based on python version.
      If python 2, install ipython 5.x (python2 is not supported in ipython 6.

"""
import os
import sys
from os.path import exists
from setuptools import setup

import versioneer

ipython_req = 'ipython'

python_2 = sys.version_info[0] == 2
def read(fname):
    with open(fname, 'rU' if python_2 else 'r') as fhandle:
        return fhandle.read()

req_path = os.path.join(os.path.dirname('__file__'), 'requirements.txt')
required = [req.strip() for req in read(req_path).splitlines() if req.strip()]
if python_2 and 'bdist_wheel' not in sys.argv:
    required = ['ipython<6' if req == 'ipython' else req for req in required]

setup(name='papermill',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Map Reduce for Notebooks',
      author='nteract contributors',
      author_email='jupyter@googlegroups.com',
      license='BSD',
      keywords="jupyter mapreduce",
      long_description=(open('README.rst').read() if exists('README.rst') else ''),
      url='https://github.com/nteract/papermill',
      packages=['papermill'],
      install_requires=required,
      entry_points={
              'console_scripts': [
                  'papermill = papermill.cli:papermill'
              ]
          }
      )
