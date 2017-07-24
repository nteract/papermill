"""Manages the Settings for Papermill"""


class Settings(object):

    __default_settings = {
        'ENVIRONMENT_VARIABLES': []
    }

    def __init__(self):

        for name, value in self.__default_settings.items():
            setattr(self, name, value)

settings = Settings()
