# Releasing

```
git tag 0.2
git push && git push --tags
rm -rf dist/*
python setup.py sdist bdist_wheel
twine upload dist/*
```
