from enum import Enum
from typing import List, Mapping
import argparse

__all__ = [
    'ArgDescriptor',
    'add_parser_arguments',
]


class ArgDescriptor(dict):

    def __init__(self, name: str,  **kwargs):
        super().__init__(**kwargs)

        self.name = name
        self.flags = kwargs.get('flags')
        if self.flags:
            self.pop('flags')
            if 'dest' not in kwargs:
                self['dest'] = name
        else:
            self.flags = [name]

        if not 'metavar' in kwargs:
            dest = self.get('dest')
            if not dest:
                dest = name
            self['metavar'] = '<%s>' % dest

    @property
    def action(self) -> str:
        return self.get('action')

    @property
    def dest(self) -> str:
        return self.get('dest')

    @property
    def choices(self) -> List[str]:
        return self.get('choices', [self.metavar])

    @property
    def metavar(self) -> str:
        return self.get('metavar')

    def is_positional(self):
        return not self.flags[0].startswith('-')

    def is_single(self):
        return (not self.is_positional()) and (not self.is_flag())

    def is_flag(self):
        if not self.action:
            return False

        return ((self.action == "store_true") or (self.action == "store_false"))

    def is_keyvalue(self):
        return False


def add_parser_arguments(
        parser: argparse.ArgumentParser,
        arg_description_set: Mapping[str, dict]):
    for arg_key in arg_description_set:
        argparse_desc = arg_description_set[arg_key]
        arg_description = ArgDescriptor(arg_key, **argparse_desc)
        parser.add_argument(*arg_description.flags, **arg_description)