import base64
import click
import yaml
from papermill.execute import execute_notebook


@click.command()
@click.argument('notebook')
@click.argument('output')
@click.option('--parameters', '-p', help="Parameters to pass to the preface.", multiple=True, nargs=2)
@click.option('--raw_parameters', '-r', help="Parameters to be read as raw string.", multiple=True, nargs=2)
@click.option('--parameters_file', '-f', help="Path to YAML file containing parameters.")
@click.option('--parameters_yaml', '-y', help="YAML string to be used as parameters.")
@click.option('--parameters_base64', '-b', help="Base64 encoded YAML string as parameters.")
def papermill(notebook, output, parameters, raw_parameters, parameters_file, parameters_yaml, parameters_base64):
    """Utility for executing a single notebook on a container."""
    if parameters_base64:
        kwargs = yaml.load(base64.b64decode(parameters_base64))
    elif parameters_yaml:
        kwargs = yaml.load(parameters_yaml)
    elif parameters_file:
        with open(parameters_file, 'r') as infile:
            kwargs = yaml.load(infile)
    else:
        # Read in Parameters
        kwargs = {}
        for name, value in parameters:
            kwargs[name] = _resolve_type(value)
        for name, value in raw_parameters:
            kwargs[name] = value

    # Notebook Execution
    execute_notebook(notebook, output, **kwargs)


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
