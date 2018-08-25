# So You Want to Contribute to Papermill!
We welcome all contributions to Papermill both large and small. We encourage you to join our community.

## Our Community Values

We are an open and friendly community. Everybody is welcome.

We encourage friendly discussions and respect for all. There are no exceptions.

All contributions are equally important. Documentation, answering questions, and fixing bugs are equally as valuable as adding new features.

Please read our entire code of conduct [here](https://github.com/nteract/nteract/blob/master/CODE_OF_CONDUCT.md). Also, check out the for the [Python](https://github.com/nteract/nteract/blob/master/CODE_OF_CONDUCT.md) code of conduct.

## Setting up Your Development Environment
Following these instructions should give you an efficient path to opening your first pull-request.

### Cloning the Papermill Repository
Fork the repository to your local Github account. Clone this repository to your local development machine.
```
git clone https://github.com/<your_account>/papermill
cd papermill
```

### Install an Editable Version
We prefer to use [conda](https://conda.io/docs/user-guide/tasks/manage-environments.html) to manage the development environment.
```
conda create -n dev
. activate env
```
or [virtualenv](https://packaging.python.org/guides/installing-using-pip-and-virtualenv/) if you prefer.
```
python3 -m virtualenv dev
source dev/bin/activate
```

Install Papermill using:
```
pip install -e .[dev]
```

_Note: When you are finished you can use `source deactivate` to go back to your base environment._

### Running Tests Locally

We need to install the development package before we can run the tests. If anything is confusing below, always resort to the relevant documentation.
```
pytest --pyargs papermill
```
The `pyargs` option allows `pytest` to interpret arguments as python package names. An advantage is that `pytest` will run in any directory, and this approach follows the `pytest` [best practices](https://docs.pytest.org/en/latest/goodpractices.html#tests-as-part-of-application-code).

Now there should be a working and editable installation of Papermill to start making your own contributions.

## So You're Ready to Pull Request

The general workflow for this will be:
1. Run local tests
2. Pushed changes to your forked repository
3. Open pull request to main repository

### Run Tests Locally

```
pytest --pyargs papermill
```

Run check manifest to ensure all files are accounted for in the repository.
```
check-manifest
```
This commands read the `MANIFEST.in` file and explicitly specify the files to include in the source distribution. You can read more about how this works [here](https://docs.python.org/3/distutils/sourcedist.html).

### Push Changes to Forked Repo

Your commits should be pushed to the forked repository. To verify this type ```git remote -v``` and ensure the remotes point to your GitHub. Don't work on the master branch!

1. Commit changes to local repository:
    ```
    git checkout -b my-feature
    git add <updated_files>
    git commit
    ```
2. Push changes to your remote repository:
    ```
    git push -u origin my-feature
    ```

### Create Pull Request

Follow [these](https://help.github.com/articles/creating-a-pull-request-from-a-fork/) instrucutions to create a pull request from a forked repository. If you are submitting a bug-fix for a specific issue make sure to reference the issue in the pull request.

There are good references to the [Git documentation](https://git-scm.com/doc) and [Git workflows](https://docs.scipy.org/doc/numpy/dev/gitwash/development_workflow.html) for more information if any of this is unfamiliar.

_Note: You might want to set a reference to the main repository to fetch/merge from there instead of your forked repository. You can do that using:_
```
git remote add upstream https://github.com/nteract/papermill
```

It's possible you will have conflicts between your repository and master. Here, `master` is meant to be synchronized with the ```upstream``` repository.  GitHub has some good [documentation](https://help.github.com/articles/resolving-a-merge-conflict-using-the-command-line/) on merging pull requests from the command line.

Happy hacking on Papermill!
