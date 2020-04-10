# Development Guide

_Note: If you haven't read the CONTRIBUTING.md instructions, make sure to do so before continuing._

## IO Sources / Sinks

To add a new input source + sink to papermill look in the `iorw.py` file for a few examples.

The `papermill_io` object at root context of the module holds the registered IO handlers. This maintains the LIFO queue of potential path consumers for any IO request. Each handler is registered to a prefix path which it uses as a prefix match against the input arguments. You'll notice `local` is the lowest order handler and is a special case we use to fall-back on if no other handler matches.

To add a new handler, simply create a new class which implements the `read`, `listdir`, `write`, and `pretty_path` class methods. `listdir` is optional, and not used by the execute method / cli command. Then add `papermill_io.register("my-new-prefix", MyNewHandler)` and papermill will pick up the new IO handler for any paths it processes.

Remember to add tests to prove your new handler works!

_Note: You can also extend the registry in your own modules to enable domain specific io extensions without needing to commit to papermill._

## Language Translations

When you wish to add a new language or kernel to papermill, look in the `translators.py` file.

Like with the iorw pattern, there is a `papermill_translators` object at the root of the file which holds all key-value mappings from kernel / language names to translators. Each Translator inherits from `Translator` which gives the basic JSON conversion structures. Then for each JSON type you'll need to add the relevant translate_type class method. Additionally, you'll want to implement the `comment` function for mapping single line comments. For languages which have a special format for assigning variables you can also override the assign method (see ScalaTranslator for an example).

Finally, register the new handler to the `papermill_translators` object. The translator name must either match the kernel or language name being processed to be used for your notebook execution. This will enable any notebook using the named kernel to use your new parameter translations.

Test additions are easy to create -- just copy the few language specific pytest methods in `test_translators.py` and swap to your new translator name / expected values.

## Engines

By default papermill uses nbconvert to process notebooks. But it's setup as a plug-n-play system so any function that can process a notebook and return the output nbformat object can be registered into papermill.

To enable a new engine, first look in `engines.py` at the `NBConvertEngine` as a working example. This class inherits from `Engine` and is required to implement the classmethod `execute_managed_notebook`. The first argument to this method is a `NotebookExecutionManager` -- which is built and passed in the Engine `execute_notebook` classmethod -- and is used to provide callback bindings for cell execution signals.

The `NotebookExecutionManager` class tracks the notebook object in progress, which is copied from the input notebook to provide functional execution isolation. It also tracks metadata updates and execution timing. In general you don't need to worry about this class except to know it has a `nb` attribute and three callbacks you can call from your engine implementation.

- `cell_start` takes a cell argument and sets the cell metadata up for execution. This triggers a notebook save.
- `cell_exception` takes a cell argument and flags the cell as failed. This does **not** trigger a notebook save (as the notebook completion after cell failure will save).
- `cell_complete` takes a cell argument and finalizes timing information in the cell metadata. This triggers a notebook save.

These functions can be optionally called to better render and populate notebooks with appropriate metadata attributes to reflect their execution. Manually saving the notebook object is unnecessary as the base class wrapper will save the notebook on notebook start and completion on your behalf. If you wish to disable saving, overwrite the `wrap_and_execute_notebook` and prevent the `output_path` from propagating to the base method call.

`papermill.execute_notebook` allows you to pass arbitrary arguments down to the engine. Make sure that engine handles keyword arguments properly. Use utility `merge_kwargs` and `remove_args` to merge and clean arguments.

To update tests you'll need to add a new test class in `test_engines.py`. Copying the `TestNBConvertEngine` class and modifying it is recommended.

## CLI / Execute

When adding an option to papermill, first look in `cli.py` and then `execute.py` for the two places to add your new configurable.

In `cli.py` you'll want to add an `@click.option` above the `papermill` method and the option name as a positional argument in the `papermill` method. These are fairly straight forward to assign, and you can refer to click's documentation for how to do all the basic options. Then you'll need to pass the argument to `execute_notebook`. We treat the CLI layer as a very light wrapper on the execute method in an attempt to both obey DRY (don't repeat yourself) and to ensure that the imported python module has the same capabilities as the CLI.

Now in `execute.py`'s `execute_notebook` we want to add the appropriate argument and default it to something sane. Add the argument to the docstring as well. Then pass or use that argument where it's needed to achieve the desired effect. Usually these options get passed to `_execute_parameterized_notebook`.

To update the tests you'll need both `test_cli.py` and `test_execute.py` to include the new option. Though the CLI tests need only check that the appropriate values get passed to `execute_notebook`.
