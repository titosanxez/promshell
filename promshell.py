import sys
from enum import Enum
import argparse

from prompt_toolkit.history import FileHistory

from promshell.shell import Shell, CommandHandler
from promshell.prometheus import rest_builder, handlers
import promshell.arguments


class PromshellAction(Enum):
    QUERY = 'query'
    SERIES = 'series'
    LABELS = 'labels'
    FETCH = 'fetch'


def program_name() -> str:
    return sys.argv[0].partition('.py')[0]


class PromShell:

    DEFAULT_CONFIG = dict(
        address='localhost:9090',
        no_fetch=False,
        history_path='./%s_history' % program_name()
    )

    PARSER_CONFIG_DEFAULT = {
        'prog': program_name(),
        'description': 'Interactive command-line interface to obtain information from Prometheus',
        'add_help': True,
        'usage': None,
        'conflict_handler': 'resolve'
    }

    PROMPT_CONFIG_DEFAULT = {
        'message': '%s> ' % program_name(),
        'complete_while_typing': False,
        'complete_in_thread': True,
        'history': FileHistory(DEFAULT_CONFIG['history_path'])
    }

    ARG_SPEC = {
        'address': dict(
            flags=['-a', '--address'],
            help='Prometheus server address',
            nargs='?',
            metavar='<address>',
            default='localhost:9090'),
        'no_fetch': dict(
            flags=['-f', '--no-fetch'],
            action='store_true',
            help='Disable fetching of Prometheus metric and labels on start',
            default=False),
        'history_path': dict(
            flags=['-p', '--history-path'],
            help='Set file path that contains the command history',
            nargs='?',
            default='./%s_history' % program_name()),
    }

    def __init__(
            self,
            address: str = DEFAULT_CONFIG['address'],
            no_fetch: bool = DEFAULT_CONFIG['no_fetch'],
            history_path: str = DEFAULT_CONFIG['history_path']):

        prompt_config = PromShell.PROMPT_CONFIG_DEFAULT.copy()
        prompt_config['history'] = FileHistory(history_path)
        self.shell = Shell(
            PromShell.PARSER_CONFIG_DEFAULT,
            prompt_config)
        self.factory = handlers.HandlerFactory(
                server_address=address)
        if not no_fetch:
            self.factory.fetch()
        self.__register_handlers()

    def __register_handlers(self):
        # prometheus operations
        self.shell.register_handler(
            PromshellAction.QUERY.value,
            self.factory.handler(handlers.HandlerFactory.QUERY),
            arguments=rest_builder.Query.ARG_SPEC,
            help='Obtain an instant query or range query')
        self.shell.register_handler(
            PromshellAction.SERIES.value,
            self.factory.handler(handlers.HandlerFactory.SERIES),
            arguments=rest_builder.Series.ARG_SPEC,
            help='Obtain series data for a specified metric and label expression')
        self.shell.register_handler(
            PromshellAction.LABELS.value,
            self.factory.handler(handlers.HandlerFactory.LABELS),
            arguments=rest_builder.Labels.ARG_SPEC,
            help='Obtain label information')
        # General
        self.shell.register_handler(
            PromshellAction.FETCH.value,
            self.FetchHandler(self),
            arguments=self.FetchHandler.ARG_SPEC,
            help='Fetch Prometheus available metrics and labels, for autocompletion'
        )

    def run(self):
        self.shell.run()

    #
    # Builtin Handlers
    #
    class FetchHandler(CommandHandler):
        ARG_SPEC = {  }

        def __init__(self, promshell):
            self.promshell: PromShell = promshell

        def handle(self, command_args) -> dict:
            self.promshell.factory.fetch()
            return dict(result='fetched OK')


if __name__ == "__main__":
    PARSER_CONFIG = {
        'prog': program_name(),
        'description': 'Interactive command-line interface to obtain information from Prometheus',
        'add_help': True
    }
    parser = argparse.ArgumentParser(**PARSER_CONFIG)
    promshell.arguments.add_parser_arguments(
        parser,
        PromShell.ARG_SPEC
    )
    arguments = parser.parse_args()
    promshell = PromShell(**vars(arguments))
    promshell.run()
