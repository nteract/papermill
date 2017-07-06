#!/usr/bin/env python
# -*- coding: utf-8 -*-

#!/usr/bin/env python


from os.path import exists
from setuptools import setup
import versioneer

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
     )
