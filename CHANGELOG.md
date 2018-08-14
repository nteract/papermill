# Change Log

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
