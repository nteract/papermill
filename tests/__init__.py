import os


def get_notebook_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notebooks', filename)
