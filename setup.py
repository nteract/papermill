#!/usr/bin/env python
# -*- coding: utf-8 -*-
""""
setup.py

See:
https://packaging.python.org/tutorials/packaging-projects/
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject

"""
import os
from setuptools import setup


local_path = os.path.dirname(__file__)
# Fix for tox which manipulates execution pathing
if not local_path:
    local_path = '.'
here = os.path.abspath(local_path)


def version():
    with open(here + '/papermill/version.py', 'r') as ver:
        for line in ver.readlines():
            if line.startswith('version ='):
                return line.split(' = ')[-1].strip()[1:-1]
    raise ValueError('No version found in papermill/version.py')


def read(fname):
    with open(fname, 'r') as fhandle:
        return fhandle.read()


def read_reqs(fname):
    req_path = os.path.join(here, fname)
    return [req.strip() for req in read(req_path).splitlines() if req.strip()]


s3_reqs = read_reqs('requirements-s3.txt')
azure_reqs = read_reqs('requirements-azure.txt')
gcs_reqs = read_reqs('requirements-gcs.txt')
hdfs_reqs = read_reqs('requirements-hdfs.txt')
all_reqs = s3_reqs + azure_reqs + gcs_reqs + hdfs_reqs
dev_reqs = read_reqs('requirements-dev.txt') + all_reqs
extras_require = {
    "test": dev_reqs,
    "dev": dev_reqs,
    "all": all_reqs,
    "s3": s3_reqs,
    "azure": azure_reqs,
    "gcs": gcs_reqs,
    "hdfs": hdfs_reqs,
}

# Get the long description from the README file
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
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
    python_requires='>=3.6',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
