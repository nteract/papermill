#!/usr/bin/env python
# -*- coding: utf-8 -*-

#!/usr/bin/env python


from os.path import exists
from setuptools import setup
import versioneer

ipython_req = 'ipython'

import sys
if sys.version_info[0] < 3 and 'bdist_wheel' not in sys.argv:
    ipython_req = 'ipython<6'

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
      install_requires=[
          'boto3',
          'click',
          'futures',
          'pyyaml',
          'nbformat',
          ipython_req,
          'nbconvert',
          'six',
          'jupyter_client',
          'pandas'
      ],
      entry_points={
              'console_scripts': [
                  'papermill = papermill.cli:papermill'
              ]
          }
     )
