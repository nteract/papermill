import logging
import math
import re
import shlex

from .exceptions import PapermillException
from .models import Parameter

logger = logging.getLogger(__name__)


class PapermillTranslators:
    '''
    The holder which houses any translator registered with the system.
    This object is used in a singleton manner to save and load particular
    named Translator objects for reference externally.
    '''

    def __init__(self):
        self._translators = {}

    def register(self, language, translator):
        self._translators[language] = translator

    def find_translator(self, kernel_name, language):
        if kernel_name in self._translators:
            return self._translators[kernel_name]
        elif language in self._translators:
            return self._translators[language]
        raise PapermillException(
            f"No parameter translator functions specified for kernel '{kernel_name}' or language '{language}'"
        )


class Translator:
    @classmethod
    def translate_raw_str(cls, val):
        """Reusable by most interpreters"""
        return f'{val}'

    @classmethod
    def translate_escaped_str(cls, str_val):
        """Reusable by most interpreters"""
        if isinstance(str_val, str):
            str_val = str_val.encode('unicode_escape')
            str_val = str_val.decode('utf-8')
            str_val = str_val.replace('"', r'\"')
        return f'"{str_val}"'

    @classmethod
    def translate_str(cls, val):
        """Default behavior for translation"""
        return cls.translate_escaped_str(val)

    @classmethod
    def translate_none(cls, val):
        """Default behavior for translation"""
        return cls.translate_raw_str(val)

    @classmethod
    def translate_int(cls, val):
        """Default behavior for translation"""
        return cls.translate_raw_str(val)

    @classmethod
    def translate_float(cls, val):
        """Default behavior for translation"""
        return cls.translate_raw_str(val)

    @classmethod
    def translate_bool(cls, val):
        """Default behavior for translation"""
        return 'true' if val else 'false'

    @classmethod
    def translate_dict(cls, val):
        raise NotImplementedError(f'dict type translation not implemented for {cls}')

    @classmethod
    def translate_list(cls, val):
        raise NotImplementedError(f'list type translation not implemented for {cls}')

    @classmethod
    def translate(cls, val):
        """Translate each of the standard json/yaml types to appropriate objects."""
        if val is None:
            return cls.translate_none(val)
        elif isinstance(val, str):
            return cls.translate_str(val)
        # Needs to be before integer checks
        elif isinstance(val, bool):
            return cls.translate_bool(val)
        elif isinstance(val, int):
            return cls.translate_int(val)
        elif isinstance(val, float):
            return cls.translate_float(val)
        elif isinstance(val, dict):
            return cls.translate_dict(val)
        elif isinstance(val, list):
            return cls.translate_list(val)
        # Use this generic translation as a last resort
        return cls.translate_escaped_str(val)

    @classmethod
    def comment(cls, cmt_str):
        raise NotImplementedError(f'comment translation not implemented for {cls}')

    @classmethod
    def assign(cls, name, str_val):
        return f'{name} = {str_val}'

    @classmethod
    def codify(cls, parameters, comment='Parameters'):
        content = f'{cls.comment(comment)}\n'
        for name, val in parameters.items():
            content += f'{cls.assign(name, cls.translate(val))}\n'
        return content

    @classmethod
    def inspect(cls, parameters_cell):
        """Inspect the parameters cell to get a Parameter list

        It must return an empty list if no parameters are found and
        it should ignore inspection errors.

        .. note::
            ``inferred_type_name`` should be "None" if unknown (set it
            to "NoneType" for null value)

        Parameters
        ----------
        parameters_cell : NotebookNode
            Cell tagged _parameters_

        Returns
        -------
        List[Parameter]
            A list of all parameters
        """
        raise NotImplementedError(f'parameters introspection not implemented for {cls}')


class PythonTranslator(Translator):
    # Pattern to capture parameters within cell input
    PARAMETER_PATTERN = re.compile(
        r"^(?P<target>\w[\w_]*)\s*(:\s*[\"']?(?P<annotation>\w[\w_\[\],\s]*)[\"']?\s*)?=\s*(?P<value>.*?)(\s*#\s*(type:\s*(?P<type_comment>[^\s]*)\s*)?(?P<help>.*))?$"
    )

    @classmethod
    def translate_float(cls, val):
        if math.isfinite(val):
            return cls.translate_raw_str(val)
        elif math.isnan(val):
            return "float('nan')"
        elif val < 0:
            return "float('-inf')"
        else:
            return "float('inf')"

    @classmethod
    def translate_bool(cls, val):
        return cls.translate_raw_str(val)

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join([f"{cls.translate_str(k)}: {cls.translate(v)}" for k, v in val.items()])
        return f'{{{escaped}}}'

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'[{escaped}]'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()

    @classmethod
    def codify(cls, parameters, comment='Parameters'):
        content = super().codify(parameters, comment)
        try:
            # Put content through the Black Python code formatter
            import black

            fm = black.FileMode(string_normalization=False)
            content = black.format_str(content, mode=fm)
        except ImportError:
            logger.debug("Black is not installed, parameters won't be formatted")
        except AttributeError as aerr:
            logger.warning(f"Black encountered an error, skipping formatting ({aerr})")
        return content

    @classmethod
    def inspect(cls, parameters_cell):
        """Inspect the parameters cell to get a Parameter list

        It must return an empty list if no parameters are found and
        it should ignore inspection errors.

        Parameters
        ----------
        parameters_cell : NotebookNode
            Cell tagged _parameters_

        Returns
        -------
        List[Parameter]
            A list of all parameters
        """
        params = []
        src = parameters_cell['source']

        def flatten_accumulator(accumulator):
            """Flatten a multilines variable definition.

            Remove all comments except on the latest line - will be interpreted as help.

            Args:
                accumulator (List[str]): Line composing the variable definition
            Returns:
                Flatten definition
            """
            flat_string = ""
            for line in accumulator[:-1]:
                if "#" in line:
                    comment_pos = line.index("#")
                    flat_string += line[:comment_pos].strip()
                else:
                    flat_string += line.strip()
            if len(accumulator):
                flat_string += accumulator[-1].strip()
            return flat_string

        # Some common type like dictionaries or list can be expressed over multiline.
        # To support the parsing of such case, the cell lines are grouped between line
        # actually containing an assignment. In each group, the commented and empty lines
        # are skip; i.e. the parameter help can only be given as comment on the last variable
        # line definition
        grouped_variable = []
        accumulator = []
        for iline, line in enumerate(src.splitlines()):
            if len(line.strip()) == 0 or line.strip().startswith('#'):
                continue  # Skip blank and comment

            nequal = line.count("=")
            if nequal > 0:
                grouped_variable.append(flatten_accumulator(accumulator))
                accumulator = []
                if nequal > 1:
                    logger.warning(f"Unable to parse line {iline + 1} '{line}'.")
                    continue

            accumulator.append(line)
        grouped_variable.append(flatten_accumulator(accumulator))

        for definition in grouped_variable:
            if len(definition) == 0:
                continue

            match = re.match(cls.PARAMETER_PATTERN, definition)
            if match is not None:
                attr = match.groupdict()
                if attr["target"] is None:  # Fail to get variable name
                    continue

                type_name = str(attr["annotation"] or attr["type_comment"] or None)
                params.append(
                    Parameter(
                        name=attr["target"].strip(),
                        inferred_type_name=type_name.strip(),
                        default=str(attr["value"]).strip(),
                        help=str(attr["help"] or "").strip(),
                    )
                )

        return params


class RTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        return 'NULL'

    @classmethod
    def translate_bool(cls, val):
        return 'TRUE' if val else 'FALSE'

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join([f'{cls.translate_str(k)} = {cls.translate(v)}' for k, v in val.items()])
        return f'list({escaped})'

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'list({escaped})'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        # Leading '_' aren't legal R variable names -- so we drop them when injecting
        while name.startswith("_"):
            name = name[1:]
        return f'{name} = {str_val}'


class ScalaTranslator(Translator):
    @classmethod
    def translate_int(cls, val):
        strval = cls.translate_raw_str(val)
        return f"{strval}L" if (val > 2147483647 or val < -2147483648) else strval

    @classmethod
    def translate_dict(cls, val):
        """Translate dicts to scala Maps"""
        escaped = ', '.join([f"{cls.translate_str(k)} -> {cls.translate(v)}" for k, v in val.items()])
        return f'Map({escaped})'

    @classmethod
    def translate_list(cls, val):
        """Translate list to scala Seq"""
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'Seq({escaped})'

    @classmethod
    def comment(cls, cmt_str):
        return f'// {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'val {name} = {str_val}'


class JuliaTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        return 'nothing'

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join([f"{cls.translate_str(k)} => {cls.translate(v)}" for k, v in val.items()])
        return f'Dict({escaped})'

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'[{escaped}]'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()


class MatlabTranslator(Translator):
    @classmethod
    def translate_escaped_str(cls, str_val):
        """Translate a string to an escaped Matlab string"""
        if isinstance(str_val, str):
            str_val = str_val.encode('unicode_escape')
            str_val = str_val.decode('utf-8')
            str_val = str_val.replace('"', '""')
        return f'"{str_val}"'

    @staticmethod
    def __translate_char_array(str_val):
        """Translates a string to a Matlab char array"""
        if isinstance(str_val, str):
            str_val = str_val.encode('unicode_escape')
            str_val = str_val.decode('utf-8')
            str_val = str_val.replace('\'', '\'\'')
        return f'\'{str_val}\''

    @classmethod
    def translate_none(cls, val):
        return 'NaN'

    @classmethod
    def translate_dict(cls, val):
        keys = ', '.join([f"{cls.__translate_char_array(k)}" for k, v in val.items()])
        vals = ', '.join([f"{cls.translate(v)}" for k, v in val.items()])
        return f'containers.Map({{{keys}}}, {{{vals}}})'

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'{{{escaped}}}'

    @classmethod
    def comment(cls, cmt_str):
        return f'% {cmt_str}'.strip()

    @classmethod
    def codify(cls, parameters, comment='Parameters'):
        content = f'{cls.comment(comment)}\n'
        for name, val in parameters.items():
            content += f'{cls.assign(name, cls.translate(val))};\n'
        return content


class CSharpTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        # Can't figure out how to do this as nullable
        raise NotImplementedError("Option type not implemented for C#.")

    @classmethod
    def translate_bool(cls, val):
        return 'true' if val else 'false'

    @classmethod
    def translate_int(cls, val):
        strval = cls.translate_raw_str(val)
        return f"{strval}L" if (val > 2147483647 or val < -2147483648) else strval

    @classmethod
    def translate_dict(cls, val):
        """Translate dicts to nontyped dictionary"""

        kvps = ', '.join([f"{{ {cls.translate_str(k)} , {cls.translate(v)} }}" for k, v in val.items()])
        return f'new Dictionary<string,Object>{{ {kvps} }}'

    @classmethod
    def translate_list(cls, val):
        """Translate list to array"""
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'new [] {{ {escaped} }}'

    @classmethod
    def comment(cls, cmt_str):
        return f'// {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'var {name} = {str_val};'


class FSharpTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        return 'None'

    @classmethod
    def translate_bool(cls, val):
        return 'true' if val else 'false'

    @classmethod
    def translate_int(cls, val):
        strval = cls.translate_raw_str(val)
        return f"{strval}L" if (val > 2147483647 or val < -2147483648) else strval

    @classmethod
    def translate_dict(cls, val):
        tuples = '; '.join([f"({cls.translate_str(k)}, {cls.translate(v)} :> IComparable)" for k, v in val.items()])
        return f'[ {tuples} ] |> Map.ofList'

    @classmethod
    def translate_list(cls, val):
        escaped = '; '.join([cls.translate(v) for v in val])
        return f'[ {escaped} ]'

    @classmethod
    def comment(cls, cmt_str):
        return f'(* {cmt_str} *)'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'let {name} = {str_val}'


class PowershellTranslator(Translator):
    @classmethod
    def translate_escaped_str(cls, str_val):
        """Translate a string to an escaped Matlab string"""
        if isinstance(str_val, str):
            str_val = str_val.encode('unicode_escape')
            str_val = str_val.decode('utf-8')
            str_val = str_val.replace('"', '`"')
        return f'"{str_val}"'

    @classmethod
    def translate_float(cls, val):
        if math.isfinite(val):
            return cls.translate_raw_str(val)
        elif math.isnan(val):
            return "[double]::NaN"
        elif val < 0:
            return "[double]::NegativeInfinity"
        else:
            return "[double]::PositiveInfinity"

    @classmethod
    def translate_none(cls, val):
        return '$Null'

    @classmethod
    def translate_bool(cls, val):
        return '$True' if val else '$False'

    @classmethod
    def translate_dict(cls, val):
        kvps = '\n '.join([f"{cls.translate_str(k)} = {cls.translate(v)}" for k, v in val.items()])
        return f'@{{{kvps}}}'

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'@({escaped})'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'${name} = {str_val}'


class BashTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        return ''

    @classmethod
    def translate_bool(cls, val):
        return 'true' if val else 'false'

    @classmethod
    def translate_escaped_str(cls, str_val):
        return shlex.quote(str(str_val))

    @classmethod
    def translate_list(cls, val):
        escaped = ' '.join([cls.translate(v) for v in val])
        return f'({escaped})'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'{name}={str_val}'


# Instantiate a PapermillIO instance and register Handlers.
papermill_translators = PapermillTranslators()
papermill_translators.register("python", PythonTranslator)
papermill_translators.register("R", RTranslator)
papermill_translators.register("scala", ScalaTranslator)
papermill_translators.register("julia", JuliaTranslator)
papermill_translators.register("matlab", MatlabTranslator)
papermill_translators.register(".net-csharp", CSharpTranslator)
papermill_translators.register(".net-fsharp", FSharpTranslator)
papermill_translators.register(".net-powershell", PowershellTranslator)
papermill_translators.register("pysparkkernel", PythonTranslator)
papermill_translators.register("sparkkernel", ScalaTranslator)
papermill_translators.register("sparkrkernel", RTranslator)
papermill_translators.register("bash", BashTranslator)


def translate_parameters(kernel_name, language, parameters, comment='Parameters'):
    return papermill_translators.find_translator(kernel_name, language).codify(parameters, comment)
