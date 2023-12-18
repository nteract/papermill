#!/usr/bin/env python
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
    with open(f"{here}/papermill/version.py") as ver:
        for line in ver.readlines():
            if line.startswith('version ='):
                return line.split(' = ')[-1].strip()[1:-1]
    raise ValueError('No version found in papermill/version.py')


def read(fname):
    with open(fname) as fhandle:
        return fhandle.read()


def read_reqs(fname, folder=None):
    path_dir = os.path.join(here, folder) if folder else here
    req_path = os.path.join(path_dir, fname)
    return [req.strip() for req in read(req_path).splitlines() if req.strip()]


s3_reqs = read_reqs('s3.txt', folder='requirements')
azure_reqs = read_reqs('azure.txt', folder='requirements')
gcs_reqs = read_reqs('gcs.txt', folder='requirements')
hdfs_reqs = read_reqs('hdfs.txt', folder='requirements')
github_reqs = read_reqs('github.txt', folder='requirements')
docs_only_reqs = read_reqs('docs.txt', folder='requirements')
black_reqs = ['black >= 19.3b0']
all_reqs = s3_reqs + azure_reqs + gcs_reqs + hdfs_reqs + github_reqs + black_reqs
docs_reqs = all_reqs + docs_only_reqs
# Temporarily remove hdfs_reqs from dev deps until the pyarrow package is available for Python 3.12
dev_reqs = read_reqs('dev.txt', folder='requirements') + s3_reqs + azure_reqs + gcs_reqs + black_reqs  # all_reqs
extras_require = {
    "test": dev_reqs,
    "dev": dev_reqs,
    "all": all_reqs,
    "s3": s3_reqs,
    "azure": azure_reqs,
    "gcs": gcs_reqs,
    "hdfs": hdfs_reqs,
    "github": github_reqs,
    "black": black_reqs,
    "docs": docs_reqs,
}

# Get the long description from the README file
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='papermill',
    version=version(),
    description='Parameterize and run Jupyter and nteract Notebooks',
    author='nteract contributors',
    author_email='nteract@googlegroups.com',
    license='BSD',
    # Note that this is a string of words separated by whitespace, not a list.
    keywords='jupyter mapreduce nteract pipeline notebook',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/nteract/papermill',
    packages=['papermill'],
    python_requires='>=3.8',
    install_requires=read_reqs('requirements.txt'),
    extras_require=extras_require,
    entry_points={'console_scripts': ['papermill = papermill.__main__:papermill']},
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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
