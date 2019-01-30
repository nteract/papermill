# Releasing

## Pre-requisites

- First check that the CHANGELOG is up to date for the next release version
- Ensure dev requirements are installed `pip install -r requirements-dev.txt`

## Push to github

Change from patch to minor or major for appropriate version updates.

```
bumpversion patch
git push && git push --tags
```

## Push to PyPi

```
rm -rf dist/*
python setup.py sdist bdist_wheel
twine upload dist/*
```
