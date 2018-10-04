import sys
from six import string_types, integer_types
from jupyter_client.kernelspec import get_kernel_spec
from .exceptions import PapermillException


class PapermillTranslators(object):
    '''
    The holder which houses any translator registered with the system.
    This object is used in a singleton manner to save and load particular
    named Translator objects for reference externally.
    '''

    def __init__(self):
        self._translators = {}

    def register(self, language, translator):
        self._translators[language] = translator

    def kernel_translator(self, kernel_name):
        kernelspec = get_kernel_spec(kernel_name)
        if kernel_name in self._translators:
            return self._translators[kernel_name]
        elif kernelspec.language in self._translators:
            return self._translators[kernelspec.language]
        raise PapermillException(
            "No parameter translator functions specified for kernel '{}' or language '{}'".format(
                kernel_name, kernelspec.language
            )
        )


class Translator(object):
    @classmethod
    def translate_raw_str(csl, val):
        """Reusable by most interpreters"""
        return '{}'.format(val)

    @classmethod
    def translate_escaped_str(cls, str_val):
        """Reusable by most interpreters"""
        if isinstance(str_val, string_types):
            str_val = str_val.encode('unicode_escape')
            if sys.version_info >= (3, 0):
                str_val = str_val.decode('utf-8')
            str_val = str_val.replace('"', r'\"')
        return '"{}"'.format(str_val)

    @classmethod
    def translate_str(cls, val):
        """Default behavior for translation"""
        return cls.translate_escaped_str(val)

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
        raise NotImplementedError('dict type translation not implemented for {}'.format(cls))

    @classmethod
    def translate_list(cls, val):
        raise NotImplementedError('list type translation not implemented for {}'.format(cls))

    @classmethod
    def translate(cls, val):
        """Translate each of the standard json/yaml types to appropiate objects."""
        if isinstance(val, string_types):
            return cls.translate_str(val)
        # Needs to be before integer checks
        elif isinstance(val, bool):
            return cls.translate_bool(val)
        elif isinstance(val, integer_types):
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
        raise NotImplementedError('comment translation not implemented for {}'.format(cls))

    @classmethod
    def assign(cls, name, str_val):
        return '{} = {}'.format(name, str_val)

    @classmethod
    def codify(cls, parameters):
        content = '{}\n'.format(cls.comment('Parameters'))
        for name, val in parameters.items():
            content += '{}\n'.format(cls.assign(name, cls.translate(val)))
        return content


class PythonTranslator(Translator):
    @classmethod
    def translate_bool(cls, val):
        return cls.translate_raw_str(val)

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join(
            ["{}: {}".format(cls.translate_str(k), cls.translate(v)) for k, v in val.items()]
        )
        return '{{{}}}'.format(escaped)

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return '[{}]'.format(escaped)

    @classmethod
    def comment(cls, cmt_str):
        return '# {}'.format(cmt_str).strip()


class RTranslator(Translator):
    @classmethod
    def translate_bool(cls, val):
        return 'TRUE' if val else 'FALSE'

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join(
            ['{} = {}'.format(cls.translate_str(k), cls.translate(v)) for k, v in val.items()]
        )
        return 'list({})'.format(escaped)

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return 'list({})'.format(escaped)

    @classmethod
    def comment(cls, cmt_str):
        return '# {}'.format(cmt_str).strip()


class ScalaTranslator(Translator):
    @classmethod
    def translate_int(cls, val):
        strval = cls.translate_raw_str(val)
        return strval + "L" if (val > 2147483647 or val < -2147483648) else strval

    @classmethod
    def translate_dict(cls, val):
        """Translate dicts to scala Maps"""
        escaped = ', '.join(
            ["{} -> {}".format(cls.translate_str(k), cls.translate(v)) for k, v in val.items()]
        )
        return 'Map({})'.format(escaped)

    @classmethod
    def translate_list(cls, val):
        """Translate list to scala Seq"""
        escaped = ', '.join([cls.translate(v) for v in val])
        return 'Seq({})'.format(escaped)

    @classmethod
    def comment(cls, cmt_str):
        return '// {}'.format(cmt_str).strip()

    @classmethod
    def assign(cls, name, str_val):
        return 'val {} = {}'.format(name, str_val)


class JuliaTranslator(Translator):
    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join(
            ["{} => {}".format(cls.translate_str(k), cls.translate(v)) for k, v in val.items()]
        )
        return 'Dict({})'.format(escaped)

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return '[{}]'.format(escaped)

    @classmethod
    def comment(cls, cmt_str):
        return '# {}'.format(cmt_str).strip()


# Instantiate a PapermillIO instance and register Handlers.
papermill_translators = PapermillTranslators()
papermill_translators.register("python", PythonTranslator)
papermill_translators.register("R", RTranslator)
papermill_translators.register("scala", ScalaTranslator)
papermill_translators.register("julia", JuliaTranslator)


def translate_parameters(kernel_name, parameters):
    return papermill_translators.kernel_translator(kernel_name).codify(parameters)
