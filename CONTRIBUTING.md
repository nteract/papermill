# So You Want to Contribute to Papermill!

We welcome all contributions to Papermill both large and small. We encourage you to join our community.

## Our Community Values

We are an open and friendly community. Everybody is welcome.

We encourage friendly discussions and respect for all. There are no exceptions.

All contributions are equally important. Documentation, answering questions, and fixing bugs are equally as valuable as adding new features.

Please read our entire [Code of Conduct](https://github.com/nteract/nteract/blob/main/CODE_OF_CONDUCT.md).

## Setting up Your Development Environment

Following these instructions should give you an efficient path to opening your first pull-request.

### Cloning the Papermill Repository

Fork the repository to your local Github account. Clone this repository to your local development machine.

```bash
git clone https://github.com/<your_account>/papermill
cd papermill
```

### Install an Editable Version

We prefer to use native venv to manage the development environment.

```bash
python3 -m venv dev
source dev/bin/activate
```

Install Papermill using:

```bash
pip install -e '.[dev]'
```

or use conda if you prefer [conda](https://conda.io/docs/user-guide/tasks/manage-environments.html):

```bash
conda create -n dev
. activate dev
```

_Note: When you are finished you can use `source deactivate` to go back to your base environment._

### Running Tests Locally

If you are contributing with documentation please jump to [building documentation.](#Building-Documentation)

We need to install the development package before we can run the tests. If anything is confusing below, always resort to the relevant documentation.

For the most basic test runs against python 3.6 use this tox subset (callable after `pip install tox`):

```bash
tox -e py36
```

This will just execute the unittests against python 3.6 in a new virtual env. The first run will take longer to setup the virtualenv, but will be fast after that point.

For a full test suite of all envs and linting checks simply run tox without any arguments

```bash
tox
```

This will require python3.6, python3.8, and python3.7 to be installed. **Note** that python 3.7 has problems with the alpha build which is the available package version on many linux distros. Local build failures with 3.7 can happen as a result (you'll see a seg fault or exist code -11).

Alternavitely pytest can be used if you have an environment already setup which works or has custom packages not present in the tox build.

```bash
pytest
```

Now there should be a working and editable installation of Papermill to start making your own contributions.

### Building Documentation

The documentation is built using the [Sphinx](http://www.sphinx-doc.org/en/master/) engine. To contribute, edit the [RestructuredText (`.rst`)](https://en.wikipedia.org/wiki/ReStructuredText) files in the docs directory to make changes and additions.

Once you are done editing, to generate the documentation, use tox and the following command from the root directory of the repository:

```bash
tox -e docs
```

This will generate `.html` files in the `/.tox/docs_out/` directory. Once you are satisfied, feel free to jump to the next section.

## So You're Ready to Pull Request

The general workflow for this will be:

1. Run local tests
2. Pushed changes to your forked repository
3. Open pull request to main repository

### Run Tests Locally

```bash
pytest --pyargs papermill
```

Run check manifest to ensure all files are accounted for in the repository.

```bash
check-manifest
```

This commands read the `MANIFEST.in` file and explicitly specify the files to include in the source distribution. You can read more about how this works [here](https://docs.python.org/3/distutils/sourcedist.html).

### Push Changes to Forked Repo

Your commits should be pushed to the forked repository. To verify this type

```bash
git remote -v
```

and ensure the remotes point to your GitHub. Don't work on the main branch!

1. Commit changes to local repository:

    ```bash
    git checkout -b my-feature
    git add <updated_files>
    git commit
    ```

2. Push changes to your remote repository:

    ```bash
    git push -u origin my-feature
    ```

### Create Pull Request

Follow [these](https://help.github.com/articles/creating-a-pull-request-from-a-fork/) instrucutions to create a pull request from a forked repository. If you are submitting a bug-fix for a specific issue make sure to reference the issue in the pull request.

There are good references to the [Git documentation](https://git-scm.com/doc) and [Git workflows](https://docs.scipy.org/doc/numpy/dev/gitwash/development_workflow.html) for more information if any of this is unfamiliar.

_Note: You might want to set a reference to the main repository to fetch/merge from there instead of your forked repository. You can do that using:_

```bash
git remote add upstream https://github.com/nteract/papermill
```

It's possible you will have conflicts between your repository and main. Here, `main` is meant to be synchronized with the ```upstream``` repository.  GitHub has some good [documentation](https://help.github.com/articles/resolving-a-merge-conflict-using-the-command-line/) on merging pull requests from the command line.

Happy hacking on Papermill!
