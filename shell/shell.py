# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.
from abc import ABC, abstractmethod
import pprint
from enum import Enum
import argparse
from typing import  Iterable

from prompt_toolkit.completion import \
    Completion,\
    Completer, \
    NestedCompleter, \
    WordCompleter
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.shortcuts import PromptSession

from shell.completion import ArgumentCompleter, ValueCompleter, CompletionContext
from shell import arguments


# ================
# Command Handling
# ================

# Interface for command handling
class CommandHandler(ABC):

    @abstractmethod
    def handle(self, command_args) -> dict:
        NotImplemented

    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        pass


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

class BuiltinAction(Enum):
    EXIT = "exit"
    HELP = "help"


class Shell:
    """
        Generic shell class. Handles the interactive command session and
        processing of commands,
    """
    @staticmethod
    def builtin_handlers_spec() -> dict():
        return {
            BuiltinAction.HELP.value: {
                'help': 'Print command help',
                'arg_spec': Shell.HelpAction.ARG_SPEC
            },
            BuiltinAction.EXIT.value: {
                'help': 'Exit shell',
                'arg_spec': Shell.ExitAction.ARG_SPEC
            }
        }

    def __init__(
            self,
            parser_config: dict,
            prompt_config: dict):
        # List of available handler_map
        self.handler_map = {}

        # Handler ArgumentParser and subparser (for help and validation)
        self.parser = argparse.ArgumentParser(**parser_config)
        self.subparser_map = {}
        self.subparsers = self.parser.add_subparsers(
                help='Available commands',
                dest='command')

        overriden_prompt_config = prompt_config.copy()
        self.completer = ShellCompleter()
        self.key_bindings = KeyBindings()

        # Escape binding
        @staticmethod
        @self.key_bindings.add(Keys.Escape)
        def on_escape(event: KeyPressEvent):
            event.current_buffer.cancel_completion()
            event.current_buffer.exit_selection()

        # Control + c binding
        @staticmethod
        @self.key_bindings.add(Keys.ControlC)
        def on_escape(event: KeyPressEvent):
            event.app.exit(result=BuiltinAction.EXIT.value)

        self.prompt = PromptSession(
            **prompt_config,
            completer=self.completer,
            key_bindings=self.key_bindings)
        # Reduce the lag for the escape key
        self.prompt.app.timeoutlen = 0.2

        # printer for result
        self.printer = pprint.PrettyPrinter(indent=4)

        # register built-in handlers
        self.register_builtin_handlers()

    def register_builtin_handlers(self):
        # Help
        self.register_handler(
            BuiltinAction.HELP.value,
            Shell.HelpAction(self),
            arguments=Shell.builtin_handlers_spec()[BuiltinAction.HELP.value]['arg_spec'],
            help=Shell.builtin_handlers_spec()[BuiltinAction.HELP.value]['help']
        )

        # Exit
        self.register_handler(
            BuiltinAction.EXIT.value,
            Shell.ExitAction(self),
            arguments=Shell.builtin_handlers_spec()[BuiltinAction.EXIT.value]['arg_spec'],
            help=Shell.builtin_handlers_spec()[BuiltinAction.EXIT.value]['help']
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
            if text is None or text.strip() == '':
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

    #
    # Builtin Handlers
    #
    class HelpAction(CommandHandler):
        ARG_SPEC = {
            'action': dict(
                help='command name',
                nargs='?',
                metavar='<command>'),
        }

        def __init__(self, shell):
            self.shell : Shell = shell

        def handle(self, command_args) -> dict:
            if command_args.action:
                self.shell.subparser_map[command_args.action].print_help()
            else:
                self.shell.parser.print_help()

            return None

        def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
            command_names = []
            for command in self.parsers:
                command_names.append(command)

            return WordCompleter(command_names).get_completions(
                context.document,
                context.event)

    class ExitAction(CommandHandler):
        ARG_SPEC = {}

        def __init__(self, shell):
            self.shell: Shell = shell

        def handle(self, command_args):
            exit()

