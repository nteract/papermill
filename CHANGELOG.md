# Change Log

## 0.19.0
**DEPRECATION CHANGE** The record, read_notebook, and read_notebooks functions
are now officially deprecated and will be removed in papermill 1.0.

- scrapbook functionality is now deprecated
- gcsfs support is expanded to cover recent releases

## 0.18.2

### Fixes
- Addressed an issue with reading encoded notebook .ipynb files in python 3.5

## 0.18.1

### Fixes
- azure missing environment variable now has a better error message and only fails lazily
- gcs connector now has a backoff to respect service rate limits

## 0.18.0

**INSTALL CHANGE** The iorw extensions now use optional dependencies.
This means that installation for s3, azure, and gcs connectors are added via:
```
pip install papermill[s3,azure,gcs]
```
or for all dependencies
```
pip install papermill[all]
```

### Features
- Optional IO extensions are now separated into different dependencies.
- Added gs:// optional dependency for google cloud storage support.
- null json fields in parmaeters now translate correctly to equivilent fields in each supported language

### Fixes
- tqdm dependencies are pinned to fetch a minimum version for auto tqdm

### Dev Improvements
- Releases and versioning patterns were made easier
- Tox is now used to capture all test and build requirements

## 0.17.0

### Features
- Log level can now be set with `--log-level`
- The working directory of papermill can be set with the `--cwd` option. This will set the executing context of the kernel but not impact input/output paths. `papermill --cwd foo bar/input_nb.ipynb bar/output_nb.ipynb` would make the notebook able to reference files in the `foo` directoy without `../foo` but still save the output notebook in the `bar` directory.
- Tox has been added for testing papermill. This makes it easier to catch linting and manifest issues without waiting for a failed Travis build.

### Fixes
- Fixed warnings for reading non-ipynb files
- Fixed `--report-mode` with parameters (and made it more compatible with JupyterLab)
- Papermill execution progress bars now render within a notebook correctly after importing seaborn
- The `--prepare-only` option no longer requires that kernels be installed locally (you can parameterize a notebook without knowing how to execute it)
- Azure IO adapter now correctly prefixes paths with the `adl://` scheme
- Tests on OSX should pass again

### Docs
- Install doc improvements
- Guide links are updated in the README
- Test docs updated for tox usage

## 0.16.2

- Injected parameter cells now respect `--report-mode`
- Logging level is only set for logger through CLI commands
- Output and input paths can be automatically passed to notebooks with the `--inject-paths` option
- Entrypoints have been added for registration of new `papermill.io` and `papermill.engine` plugins via setup files

## 0.16.1

- Fixed issue with azure blob io operations

## 0.16.0

- Added engines abstraction and command line argument
- Moved some nbconvert wrappers out of papermill
- Added Azure blob storage support
- Fixed botocore upgrade comptability issue (all version of boto now supported again)
- Removed whitelisted environment variable assignment

## 0.15.1

- Added support for Julia kernels
- Many improvements to README.md and documentation
- nbconvert dependency pinned to >= 5.3
- Improved error handling for missing directories
- Warnings added when an unexpected file extension is used
- Papermill version is visible to the CLI
- More messages us logging module now (and can be filtered accordingly)
- Binder link from README was greatly improved to demostrate papermill features

## 0.15.0

- Moved translator functions into registry
- Added development guide to help new contributors
- Travis, coverage, linting, and doc improvements
- Added support for Azure data lake sources
- Added python 3.7 testing

## 0.14.2

- Added output flushing for log-output option

## 0.14.1

- Upgraded executor to stream outputs during execution
- Fixed UTF-8 encoding issues for windows machines
- Added [black](https://github.com/ambv/black) code formatter rules (experimental)
- Contributors document added
- Added report-mode option for hiding inputs

## 0.13.4 (no code changes)

- Release manifest fix

## 0.13.3

- Fixed scala int vs long assignment

## 0.13.2

- Pip 10 fixes

## 0.13.1

- iPython pin to circumvent upstream issue

## 0.13.0

- Added prepare-only flag for parameterizing without processing a notebook
- Fixed cell number display on failed output notebooks
- Added scala language support

## 0.12.6

- Changed CLI outputs from papermill messaging to stderr
- Changed IOResolvers to perseve ordering of definition in resolving paths

## 0.12.5

- Set click disable_unicode_literals_warning=True to disable unicode literals

## 0.12.4

- Added universal wheel support
- Test coverage for s3 improved

## 0.12.3

- Added start timeout option for slow booting kernels

## 0.12.2

- Added options around tqdm
- Fixed an S3 decoding issue

## 0.12.1

- ip_display improvements
- Docstring improvements

## 0.12.0

- Added type preservation for r and python parameters
- Massive test coverage improvements
- Codebase style pass
