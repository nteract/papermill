# Releasing

## Prerequisites

- First check that the CHANGELOG is up to date for the next release version
- Ensure dev requirements are installed `pip install -r requirements-dev.txt`

## Push to GitHub

Change from patch to minor or major for appropriate version updates.

```bash
bumpversion patch
git push upstream && git push upstream --tags
```

## Push to PyPI

```bash
rm -rf dist/*
rm -rf build/*
python setup.py sdist bdist_wheel
twine upload dist/*
```
