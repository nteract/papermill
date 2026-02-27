# Change Log

## 2.7.0

### Highlights

- Drop Python 3.8 and 3.9, add Python 3.13 support
- Drop `ansicolors` dependency
- Modernize packaging to use `pyproject.toml`

### Changes

- Add Python 3.13 support, drop Python 3.8/3.9 [#828](https://github.com/nteract/papermill/pull/828)
- Drop the dependency on `ansicolors` [#822](https://github.com/nteract/papermill/pull/822)
- Replace deprecated `datetime.utcnow()` [#823](https://github.com/nteract/papermill/pull/823)
- Modernize packaging to use `pyproject.toml` [#837](https://github.com/nteract/papermill/pull/837)
- Changed parameter inspection to raise the same error messages as other pathways for missing kernel name and language

### Bug Fixes

- Fix failing tests in CI, pin `azure-datalake-store` [#826](https://github.com/nteract/papermill/pull/826)
- Fix skipped HDFS tests for Python 3.12 [#839](https://github.com/nteract/papermill/pull/839)
- Unskip tests that were previously failing [#846](https://github.com/nteract/papermill/pull/846)

### Dev / CI

- Add `pyproject-fmt` and `validate-pyproject` pre-commit hooks [#858](https://github.com/nteract/papermill/pull/858)
- Add Dependabot for GitHub Actions [#857](https://github.com/nteract/papermill/pull/857)
- Update pre-commit config [#843](https://github.com/nteract/papermill/pull/843)
- Update CONTRIBUTING.md [#842](https://github.com/nteract/papermill/pull/842) [#847](https://github.com/nteract/papermill/pull/847)
- Update docs/RTD configuration [#805](https://github.com/nteract/papermill/pull/805) [#836](https://github.com/nteract/papermill/pull/836)
- Bump CI actions to latest versions [#852](https://github.com/nteract/papermill/pull/852) [#853](https://github.com/nteract/papermill/pull/853) [#854](https://github.com/nteract/papermill/pull/854) [#855](https://github.com/nteract/papermill/pull/855)

## 2.6.0

- bring back strip_color and remove ANSI color codes from exception traceback [#791](https://github.com/nteract/papermill/pull/791)
- cleaned up documentation [#790](https://github.com/nteract/papermill/pull/790)
- prevent error override, fix traceback type [#788](https://github.com/nteract/papermill/pull/788)
- Upgrade tests to moto v5 [#779](https://github.com/nteract/papermill/pull/779)
- raise PapermillExecutionError when CellExecutionError is raised without cell error output [#786](https://github.com/nteract/papermill/pull/786)
- make progress_bar param accept a dict [#778](https://github.com/nteract/papermill/pull/778)
- Fix nbformat to 5.2.0 to cell None type [#770](https://github.com/nteract/papermill/pull/770)
- Use f-strings where possible [#762](https://github.com/nteract/papermill/pull/762)
- Unmark wheel as universal [#764](https://github.com/nteract/papermill/pull/764)
