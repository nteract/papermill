import base64
import click
import yaml
from papermill.execute import execute_notebook
from papermill.iorw import read_yaml_file


@click.command()
@click.argument('notebook')
@click.argument('output')
@click.option('--parameters', '-p', help="Parameters to pass to the parameters cell.", multiple=True, nargs=2)
@click.option('--raw_parameters', '-r', help="Parameters to be read as raw string.", multiple=True, nargs=2)
@click.option('--parameters_file', '-f', help="Path to YAML file containing parameters.")
@click.option('--parameters_yaml', '-y', help="YAML string to be used as parameters.")
@click.option('--parameters_base64', '-b', help="Base64 encoded YAML string as parameters.")
@click.option('--kernel', '-k', help="Kernel name to run the notebook with.")
def papermill(notebook, output, parameters, raw_parameters, parameters_file, parameters_yaml, parameters_base64,
              kernel):
    """Utility for executing a single notebook on a container."""
    if parameters_base64:
        parameters_final = yaml.load(base64.b64decode(parameters_base64))
    elif parameters_yaml:
        parameters_final = yaml.load(parameters_yaml)
    elif parameters_file:
        parameters_final = read_yaml_file(parameters_file)
    else:
        # Read in Parameters
        parameters_final = {}
        for name, value in parameters:
            parameters_final[name] = _resolve_type(value)
        for name, value in raw_parameters:
            parameters_final[name] = value

    # Notebook Execution
    execute_notebook(notebook, output, parameters_final, kernel_name=kernel)


def _resolve_type(value):
    if value == "True":
        return True
    elif value == "False":
        return False
    elif value == "None":
        return None
    elif _is_float(value):
        return float(value)
    elif _is_int(value):
        return int(value)
    else:
        return value


def _is_int(value):
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_float(value):
    try:
        float(value)
    except ValueError:
        return False
    return "." in value


if __name__ == "__main__":
    papermill()
