#!/usr/bin/env bash

# run_tests.sh

pytest -vv --maxfail=3 --cov=papermill papermill/tests
coverage report -m
coverage html

