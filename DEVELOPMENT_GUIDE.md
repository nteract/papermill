# Development Guide

_Note: If you haven't read the CONTRIBUTING.md instruction, make sure to do so first before continuing._

## IO Sources / Sinks

To add a new input source + sink to papermill look in the `iorw.py` file for a few examples.

The `papermill_io` object at root context of the module holds the registered IO handlers. This maintains the LIFO queue of potential path consumers for any IO request. Each handler is registered to a prefix path which it uses as a prefix match against the input arguments. You'll notice `local` is the lowest order handler and is a special case we use to fall-back on if no other handler matches.

To add a new handler, simply create a new class which implements the `read`, `listdir`, `write`, and `pretty_path` class methods. `listdir` is optional, and not used by the execute method / cli command. Then add `papermill_io.register("my-new-prefix", MyNewHandler)` and papermill will pick up the new IO handler for any paths it processes.

Remember to add tests to prove your new handler works!

_Note: You can also extend the registry in your own modules to enable domain specific io extensions without needing to commit to papermill._

## Language Translations

When you wish to add a new language or kernel to papermill, look in the `translators.py` file.

Like with the iorw pattern, there is a `papermill_translators` object at the root of the file which holds all key-value mappins from kernel / language names to translators. Each Translator inherits from TranslatorBase which gives the basic JSON conversion structures. Then for each JSON type you'll need to add a the relevant translate_type class method. Additionally, you'll want to implement the `comment` function for mapping single line comments. For languages which have a special format for assigning variables you can also override the assign method (see ScalaTranslator for an example).

Finally, register the new handler to the `papermill_translators` object. The translator name must either match the kernelor language name being processed to be used for your notebook execution. This will enable any notebook using the named kernel to use your new parameter translations.

Test additions are easy to create -- just copy the few language specific pytest methods in `test_translators.py` and swap to your new translator name / expected values.

## CLI / Execute

When adding an option to papermill, first look in `cli.py` and then `execute.py` for the two places to add your new configurable.

In `cli.py` you'll want to add an `@click.option` above the `papermill` method and the option name as a positional argument in the `papermill` method. These are fairly straight forward to assign, and you can refer to click's documentation for how to do all the basic options. Then you'll need to pass the argument to `execute_notebook`. We treat the CLI layer as a very light wrapper on the execute method in an attempt to both obey DRY (don't repeat yourself) and to ensure that the imported python module has the same capabilities as the CLI.

Now in `execute.py`'s `execute_notebook` we want to add the appropriate argument and default it to something sane. Add the argument to the docstring as well. Then pass or use that argument where it's needed to achieve the desired effect. Usually these options get passed to `_execute_parameterized_notebook`.

To update the tests you'll need both `test_cli.py` and `test_execute.py` to include the new option. Though the CLI tests need only check that the appropiate values get passed to `execute_notebook`.
