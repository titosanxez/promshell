# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.
import http.client
import pprint
from enum import Enum
import argparse
from typing import Mapping, List, Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import \
    Completion,\
    Completer, \
    NestedCompleter, \
    WordCompleter

from . import arguments
from .completion import ArgumentCompleter, ValueCompleter, CompletionContext
from .prometheus import *
from .handler import CommandHandler
from . import arguments


# ==============================================
# Sub-commands Actions handled by PromStat class
# ==============================================

class BuiltinAction(Enum):
    EXIT = "exit"
    HELP = "help"


class ExitAction(CommandHandler):
    ARG_SPEC = {}

    def __init__(self, prom_stat):
        self.prom_stat = prom_stat

    def handle(self, command_args):
        exit()


class HelpAction(CommandHandler):
    ARG_SPEC = {
        'action': dict(
            help='command name',
            nargs='?',
            metavar='<command>'),
    }

    def __init__(self, parsers: Mapping[str, argparse.ArgumentParser]):
        self.parsers = parsers

    def handle(self, command_args) -> dict:
        if command_args.action:
            self.parsers[command_args.action].print_help()
        else:
            self.parsers[BuiltinAction.HELP.value].print_help()

        return None

    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        command_names = []
        for command in self.parsers:
            command_names.append(command)

        return WordCompleter(command_names).get_completions(
            context.document,
            context.event)


# ==============
# Autocompletion
# ==============

class ShellCompleter(Completer):

    def __init__(self):
        self.description = {}
        self.nested = NestedCompleter.from_nested_dict(self.description)

    def get_completions(self, document, complete_event):
        return self.nested.get_completions(document, complete_event)

    def set_completer(
            self,
            name: str,
            arg_comp: ArgumentCompleter):
        self.description[name] = arg_comp
        self.nested = NestedCompleter.from_nested_dict(self.description)


# ==========
# Main Class
# ==========

class ShellProperty:
    def __init__(self):
        self.prompt_name = ""
        self.address = ""


class Shell:
    """
        Generic shell class. Handles the interactive command session and
        processing of commands,
    """
    BUILTIN_HANDLERS_SPEC = {
        BuiltinAction.HELP.value: {
            'help': 'print a command help',
            'arg_spec': HelpAction.ARG_SPEC
        },
        BuiltinAction.EXIT.value: {
            'help': 'exits the shell',
            'arg_spec': ExitAction.ARG_SPEC
        }
    }

    def __init__(self, shell_name: str):
        # List of available handler_map
        self.handler_map = {}

        # Handler ArgumentParser and subparser (for help and validation)
        self.parser = argparse.ArgumentParser(
                prog=shell_name,
                description='Simple command-line interface to access DDS metrics from Prometheus',
                add_help=True,
                usage=None,
                conflict_handler='resolve')
        self.subparser_map = {}
        self.subparsers = self.parser.add_subparsers(
                help='available commands',
                dest='command')

        self.completer = ShellCompleter()
        self.prompt = PromptSession(
                message='%s> ' % shell_name,
                completer=self.completer,
                complete_while_typing=False,
                complete_in_thread=True,
                history=FileHistory("./test_hist"))
        
        # printer for result
        self.printer = pprint.PrettyPrinter(indent=4)

        # register built-in handlers
        self.register_builtin_handlers()

    def register_builtin_handlers(self):
        # Help
        self.register_handler(
            BuiltinAction.HELP.value,
            HelpAction(self.subparser_map),
            arguments=Shell.BUILTIN_HANDLERS_SPEC[BuiltinAction.HELP.value]['arg_spec'],
            help=Shell.BUILTIN_HANDLERS_SPEC[BuiltinAction.HELP.value]['help']
        )

        # Exit
        self.register_handler(
            BuiltinAction.EXIT.value,
            ExitAction(self),
            arguments=Shell.BUILTIN_HANDLERS_SPEC[BuiltinAction.EXIT.value]['arg_spec'],
            help=Shell.BUILTIN_HANDLERS_SPEC[BuiltinAction.EXIT.value]['help']
        )

    def register_handler(
            self,
            name: str,
            handler: CommandHandler,
            **kwargs):
        help_desc = kwargs.get('help')
        parser = self.subparsers.add_parser(
            name,
            add_help=True,
            help=help_desc,
            conflict_handler='resolve')
        arg_desc_set = kwargs.get('arguments')
        if arg_desc_set:
            arguments.add_parser_arguments(parser, arg_desc_set)

        self.subparser_map[name] = parser
        self.handler_map[name] = handler
        self.completer.set_completer(
            name,
            ArgumentCompleter(arg_desc_set, Shell.HandlerValueCompleter(handler)))

    def run(self):
        while True:
            text = self.prompt.prompt()
            if text.strip() == '':
                continue

            # dispatch to appropriate handler
            arguments = None
            try:
                command_spec = text.strip().split(' ')
                arguments = self.parser.parse_args(command_spec)
            except SystemExit:
                continue

            try:
                # promStat.parser.exit = parser_exit
                # parse input: obtain list of commad words separated by space
                result = self.handler_map[arguments.command].handle(arguments)
                if result:
                    self.printer.pprint(result)
            except Exception as exc:
                print("command error:", exc)

    #
    # Proxy implementation of a ValueCompleter using a CommandHandler
    #
    class HandlerValueCompleter(ValueCompleter):
        def __init__(self, handler: CommandHandler):
            self.handler = handler

        def get_completions(self, context) -> Iterable[Completion]:
            return self.handler.get_completions(context)

