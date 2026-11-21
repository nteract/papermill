"""Regression tests for running papermill with numpy v2 installed (issue #800).

numpy 2.0 removed a number of long-deprecated aliases and methods, e.g.
``np.float_``, ``np.NaN``, ``np.Inf``, ``np.alltrue``, ``np.bool8`` and the
``ndarray.ptp`` method. papermill itself does not import numpy, but it executes
notebooks in kernels where numpy v2 is installed and it translates parameter
values that may be numpy scalars. The ``dev``/``test`` extras install
``numpy>=2`` so these tests run under numpy v2 in CI; the whole module is
skipped when numpy is not installed at all.
"""

import nbformat
import pytest

from .. import inspect_notebook, translators
from ..execute import execute_notebook
from ..iorw import load_notebook_node
from . import kernel_name

np = pytest.importorskip('numpy', reason='numpy is not installed')


def _write_notebook(path, sources, parameters_cell=None):
    nb = nbformat.v4.new_notebook()
    nb.metadata.kernelspec = {'display_name': 'Python 3', 'language': 'python', 'name': kernel_name}
    nb.metadata.language_info = {'name': 'python'}
    if parameters_cell is not None:
        cell = nbformat.v4.new_code_cell(parameters_cell)
        cell.metadata.tags = ['parameters']
        nb.cells.append(cell)
    for source in sources:
        nb.cells.append(nbformat.v4.new_code_cell(source))
    nbformat.write(nb, str(path))


def _stream_text(nb):
    return ''.join(
        output.get('text', '') for cell in nb.cells for output in cell.outputs if output.output_type == 'stream'
    )


def _assert_no_errors(nb):
    errors = [output for cell in nb.cells for output in cell.outputs if output.output_type == 'error']
    assert not errors, f'Notebook execution raised errors: {errors}'


def test_numpy_v2_removed_apis():
    """Pin down the numpy v2 API removals that issue #800 is about.

    When the suite runs under numpy v2 (the dev/test extras install
    ``numpy>=2``) the removed aliases must be gone and their numpy-2-compatible
    replacements must work, so the execution tests below genuinely exercise
    numpy v2.
    """
    major = int(np.__version__.split('.')[0])
    if major < 2:
        pytest.skip('numpy v1 installed; removed-alias checks only apply to numpy v2')
    for alias in ('NaN', 'NAN', 'Inf', 'Infinity', 'float_', 'complex_', 'bool8', 'alltrue', 'sometrue', 'unicode_'):
        assert not hasattr(np, alias), f'np.{alias} should have been removed in numpy 2'
    arr = np.arange(3)
    assert not hasattr(arr, 'ptp')  # ndarray.ptp method was removed in numpy 2
    assert np.ptp(arr) == 2  # function form works in both numpy 1.x and 2.x
    assert np.isnan(np.nan)  # np.nan works in both; np.NaN was removed in numpy 2
    assert np.all(arr >= 0)  # np.all works in both; np.alltrue was removed in numpy 2
    assert np.float64(1.5) == 1.5  # np.float64 works in both; np.float_ was removed in numpy 2


def test_execute_notebook_under_numpy_v2(tmp_path):
    """execute_notebook must run notebooks that use numpy when numpy v2 is installed (issue #800)."""
    nb_path = tmp_path / 'numpy_v2.ipynb'
    out_path = tmp_path / 'numpy_v2.executed.ipynb'
    _write_notebook(
        nb_path,
        [
            'import numpy as np\n'
            'arr = np.arange(6, dtype=np.float64)\n'
            'assert np.ptp(arr) == 5.0  # ndarray.ptp method removed in numpy 2\n'
            'assert np.isnan(np.nan)  # np.NaN removed in numpy 2\n'
            'assert np.all(arr >= 0)  # np.alltrue removed in numpy 2\n'
            "print('numpy', np.__version__)\n"
            "print('result', float(np.float64(3.5)))  # np.float_ removed in numpy 2\n"
        ],
    )
    execute_notebook(str(nb_path), str(out_path), kernel_name=kernel_name)
    nb = load_notebook_node(str(out_path))
    _assert_no_errors(nb)
    text = _stream_text(nb)
    assert f'numpy {np.__version__}' in text
    assert 'result 3.5' in text


def test_execute_notebook_with_numpy_scalar_parameters(tmp_path):
    """Numpy scalar parameters (e.g. np.float64) must be translated correctly under numpy v2."""
    nb_path = tmp_path / 'numpy_params.ipynb'
    out_path = tmp_path / 'numpy_params.executed.ipynb'
    _write_notebook(
        nb_path,
        ['import math\nassert value == 2.5\nassert math.isnan(nan_value)\nprint("params ok")'],
        parameters_cell='value = 0.0\nnan_value = 0.0',
    )
    execute_notebook(
        str(nb_path),
        str(out_path),
        parameters={'value': np.float64(2.5), 'nan_value': np.nan},
        kernel_name=kernel_name,
    )
    nb = load_notebook_node(str(out_path))
    _assert_no_errors(nb)
    assert 'params ok' in _stream_text(nb)


def test_inspect_notebook_under_numpy_v2(tmp_path):
    """inspect_notebook must keep working on notebooks when numpy v2 is installed (issue #800)."""
    nb_path = tmp_path / 'numpy_inspect.ipynb'
    _write_notebook(nb_path, ["print('hello')"], parameters_cell="value: float = 1.5\nname: str = 'x'")
    params = inspect_notebook(str(nb_path))
    assert set(params) == {'value', 'name'}
    assert params['value']['inferred_type_name'] == 'float'


@pytest.mark.parametrize(
    'value,expected',
    [
        (np.float64(1.5), '1.5'),
        (np.float64(-2.5), '-2.5'),
        (np.nan, "float('nan')"),
        (np.float64('nan'), "float('nan')"),
        (np.inf, "float('inf')"),
        (np.float64('inf'), "float('inf')"),
        (np.float64('-inf'), "float('-inf')"),
    ],
)
def test_translate_numpy_float_scalars_python(value, expected):
    # np.float64 subclasses float in both numpy 1.x and 2.x, and np.nan / np.inf
    # are the numpy-2-compatible spellings of the removed np.NaN / np.Inf aliases.
    assert translators.PythonTranslator.translate(value) == expected


def test_codify_numpy_scalar_parameter():
    content = translators.PythonTranslator.codify({'value': np.float64(2.5)})
    assert 'value = 2.5' in content
