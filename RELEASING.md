# Releasing

## Pre-requisites

- First check that the CHANGELOG is up to date for the next release version
- Ensure `wheel>=0.31.0`, `setuptools>=38.6.0`, and `twine>=1.11.0` (or long readme will be malformed)

## Push to github

```
git tag 0.2
git push && git push --tags
```

## Push to PyPi

```
rm -rf dist/*
python setup.py sdist bdist_wheel
twine upload dist/*
```
