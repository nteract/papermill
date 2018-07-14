# So You Want to Contribute to Papermill...
We welcome all contributions to Papermill both large and small. We encourage you
to join our community.

## Our Community Values

We are an open and friendly community. Everybody is welcome.

We encourage friendly discussions and respect for all. No exceptions.

All contributions are equally important. Documentation, answering questions, and
fixing bugs are equally as valuable as adding new features.

Check out <https://www.python.org/psf/codeofconduct/> for the Python code of conduct.

## Setting up Your Development Environment
Following these instructions should give you an efficient path to opening your first pull-request.

### Cloning the Papermill Repository
Fork the repository to your local Github account. Clone this repository to your local development machine.
```buildoutcfg
git clone https://github.com/<your_account>/papermill
cd papermill
```

### Install an Editable Version
We prefer to use [conda](https://conda.io/docs/user-guide/tasks/manage-environments.html) to manage the development environment. 
```buildoutcfg
conda create -n dev
. activate env
``` 
or [virtualenv](https://packaging.python.org/guides/installing-using-pip-and-virtualenv/) if you prefer.
```buildoutcfg
python3 -m virtualenv dev
source dev/bin/activate 
```

```buildoutcfg
pip install -e .
```

### Running Tests Locally
We need to install the development package before we can run the tests.
```buildoutcfg
pip install papermill[dev]
py.test --pyargs papermill
```
If the installation worked properly the tests will pass.
## So You're Ready to Pull Request
The general workflow for this will be: Run Local Test 

### Run Tests Locally
```buildoutcfg
py.test --pyargs papermill
```

### Push Changes to Forked Repo
Your commits should be pushed to the forked repository. To verify this type ```git remote -v``` and 
ensure the remotes point to your GitHub. Don't work on the master branch!

1. Commit changes to local repository:
    ```
    git checkout -b my-feature
    git add <updated_files>
    git commit
    ```
2. Push changes to your remote repository:
    ```buildoutcfg
    git push -u origin my-feature 
    ```   
### Create Pull Request 
Follow [these](https://help.github.com/articles/creating-a-pull-request-from-a-fork/) instrucutions to create a
pull request from a forked repository. There are good references to the [Git docs](https://git-scm.com/doc) and 
[Git workflows](https://docs.scipy.org/doc/numpy/dev/gitwash/development_workflow.html) 
for more information.

Note: You might want to set a reference to the main repository to fetch/merge instead of your forked repository.
You can do that using:
```buildoutcfg
git remote add upstream https://github.com/nteract/papermill
```

It's possible you will have merge conflicts between your repository and master. Here, master will be synchronized
with the ```upstream``` repository.  GitHub has some good
[documentation](https://help.github.com/articles/resolving-a-merge-conflict-using-the-command-line/)
on merging pull requests from the command line.
