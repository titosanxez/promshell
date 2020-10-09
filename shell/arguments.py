from enum import Enum
from typing import List, Mapping
import argparse

__all__ = [
    'ArgDescriptor',
    'add_parser_arguments',
]


class ArgDescriptor(dict):
    """
    Class to represent the specification of a command-line argument.
    The class is a dictionary that mimics the same attributes that
    `argparse.ArgumentParser.add_argument()` expects plus one additional keyword
    to specify the option flags for non-positional arguments.

    The resulting dictionary for the `argparse` is generated using the same keywords
    as specified except:
    - `dest`: set to `name`  if not present in kwargs
    - `metavar`: set to `dest` or `name` for non-witch parameters, if
        not present in kwargs

    :param name: argument unique key identifier name.
    :param kwargs: same keywords than for `argparse.ArgumentParser.add_argument()`
    plus `flags`, to specify the option flags for non-positional arguments.
    """
    def __init__(self, name: str,  flags: str = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.flags = flags

        if flags:
            if 'dest' not in kwargs:
                self['dest'] = name
        else:
            self.flags = [name]

        if not self.is_switch():
            if not 'metavar' in kwargs:
                dest = self.get('dest')
                if not dest:
                    dest = name
                self['metavar'] = '<%s>' % dest

    @property
    def action(self) -> str:
        """
        :return: argument action or None if unspecified
        :rtype: str
        """
        return self.get('action')

    @property
    def dest(self) -> str:
        """
        :return: argument Namespace destination field name or None if unspecified
        :rtype: str
        """
        return self.get('dest')

    @property
    def choices(self) -> List[str]:
        """
        :return: argument choices or [<metavar>] if unspecified
        :rtype: List[str]
        """
        return self.get('choices', [self.metavar])

    @property
    def metavar(self) -> str:
        """
        :return: argument metavar or None if unspecified
        :rtype: str
        """
        return self.get('metavar')

    def is_positional(self) -> bool:
        """
        :return: whether this argument is positional
        :rtype: bool
        """
        return not self.flags[0].startswith('-')

    def is_option_flag(self) -> bool:
        """
        :return: wether this argument is a flag/option argument
        :rtype: bool
        """
        return (not self.is_positional()) and (not self.is_switch())

    def is_switch(self):
        """
        :return: whether this argument is a switch option flag (no value expected)
        :rtype: bool
        """
        if not self.action:
            return False

        return (self.action == "store_true") or (self.action == "store_false")


def add_parser_arguments(
        parser: argparse.ArgumentParser,
        arg_description_set: Mapping[str, dict]) -> None:
    """
        Adds all the arguments according to the specified argument descriptor set.

        This operation calls argparse.ArgumentParser.add_argument() for each argument
        descriptor, using `flags` as name_or_flags parameter and the descriptor itself
        as kwargs.

        :param parser: the parser to which the arguments are added
        :param arg_description_set: argument descriptor specification as as
            a dictionary with the keywords to pass to the .ArgDescriptor constructor
    """

    for arg_key in arg_description_set:
        argparse_desc = arg_description_set[arg_key]
        arg_description = ArgDescriptor(arg_key, **argparse_desc)
        parser.add_argument(*arg_description.flags, **arg_description)