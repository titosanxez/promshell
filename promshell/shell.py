# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.
import sys
import http.client
import pprint
import json
from enum import Enum
import argparse

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, NestedCompleter

from promshell.completion import ArgumentCompleter
from promshell.prometheus import *
from promshell.handler import CommandHandler

# ==============================================
# Sub-commands Actions handled by PromStat class
# ==============================================

class ShellAction(Enum):
    EXIT = "exit"
    QUIT = "quit"
    HELP = "help"

class PromCommand(Enum):
    QUERY = "query"
    SERIES = "series"
    INSTANCE = "instance"
    LABELS = "labels"


class ExitAction(CommandHandler):

    def handle(self, command_args):
       exit()

    def help(self):
        return 'close prompt and exit'
    
    def setup_argparser(self, parser):
        pass

class HelpAction(CommandHandler):
    def __init__(self, prom_stat):
        self.prom_stat = prom_stat

    def handle(self, command_args):
        if command_args.value == None:
           self.prom_stat.parser.print_help()
        else:
            self.prom_stat.subparser_map[command_args.value].print_help()

    def help(self):
        return 'print the command help'
       
    def setup_argparser(self, parser):
        parser.add_argument(
            'value',
            nargs='?',
            help='command name')



# ==============
# Autocompletion
# ==============

COMMAND_SYNTAX_DESCRIPTION_TEMPLATE = {
    PromCommand.QUERY.value: ArgumentCompleter(
            Query.ARG_DESCRIPTION),
    PromCommand.SERIES.value: ArgumentCompleter(
            Series.ARG_DESCRIPTION),
    PromCommand.INSTANCE.value: None,
    PromCommand.LABELS.value: ArgumentCompleter(
            Labels.ARG_DESCRIPTION),
    ShellAction.QUIT.value: None,
    ShellAction.HELP.value: None
}

class PromStatCompleter(Completer):

    def __init__(self, nested_description):
        self.nested = NestedCompleter.from_nested_dict(
                COMMAND_SYNTAX_DESCRIPTION_TEMPLATE)
        self.description = COMMAND_SYNTAX_DESCRIPTION_TEMPLATE.copy()

    def get_completions(self, document, complete_event):
        return self.nested.get_completions(document, complete_event)

    def update_metrics(self, metric_list):
        #set metrics for <exp> positional parameter in Query
        query_desc = Query.ARG_DESCRIPTION.copy()
        for arg in query_desc:
            if arg.is_positional() and arg.name == '<exp>':
                arg.value = metric_list
        self.description[PromCommand.QUERY.value] = ArgumentCompleter(query_desc)

        # set metrics for <metric> positional parameter in Series
        series_desc = Series.ARG_DESCRIPTION.copy()
        for arg in series_desc:
            if arg.is_positional() and arg.name == '<metric>':
                arg.value = metric_list
        self.description[PromCommand.SERIES.value] = ArgumentCompleter(series_desc)

        self.nested = NestedCompleter.from_nested_dict(self.description)

    def update_labels(self, label_list):
        # set metrics for <exp> positional parameter in Query
        label_desc = Labels.ARG_DESCRIPTION.copy()
        for arg in label_desc:
            if arg.name == '<label>':
                arg.value = label_list
        self.description[PromCommand.LABELS.value] = ArgumentCompleter(label_desc)

        # set labels for -l option parameter in Series
        series_desc = Series.ARG_DESCRIPTION.copy()
        for arg in series_desc:
            if arg.name == '-l':
                arg.value = label_list
        self.description[PromCommand.SERIES.value] = ArgumentCompleter(series_desc)

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
        Main rtiddsstat class. Handles the interactive command session and
        processing of commands,
    """
    
    def __init__(self, property):
        self.http_conn = http.client.HTTPConnection(property.address)
        # List of available handler_map
        self.handler_map = {
            PromCommand.QUERY.value : GetQuery(self.http_conn),
            PromCommand.SERIES.value : GetSeries(self.http_conn),
            #PromCommand.INSTANCE.value : GetInstance(self.http_conn),
            PromCommand.LABELS.value : GetLabels(self.http_conn),
            ShellAction.QUIT.value : ExitAction(),
            ShellAction.HELP.value : HelpAction(self)
        }

        # Handler ArgumentParser and subparser (for help and validation)
        self.parser = argparse.ArgumentParser(
                prog=property.prompt_name,
                description='Simple command-line interface to access DDS metrics from Prometheus',
                add_help=True,
                usage=None,
                conflict_handler='resolve')
        #self.parser.add_argument("unknown", help=argparse.SUPPRESS)
        self.subparser_map = {}
        self.__init_subparsers()

        self.completer = PromStatCompleter(
                COMMAND_SYNTAX_DESCRIPTION_TEMPLATE)
        self.prompt = PromptSession(
                message='%s> ' % property.prompt_name,
                completer=self.completer,
                complete_while_typing=False,
                complete_in_thread=True,
                history=FileHistory("./test_hist"))
        
        #printer for result
        self.printer = pprint.PrettyPrinter(indent=4)

    def __init_subparsers(self):
        subparsers = self.parser.add_subparsers(
                help='available commands',
                dest='command')                
        for name, handler in self.handler_map.items():
            handler_parser = subparsers.add_parser(
                    name,
                    add_help=True,
                    help=handler.help(),
                    conflict_handler='resolve')
            handler.setup_argparser(handler_parser)
            self.subparser_map[name] = handler_parser


    def __get_command_desc(self):
            pass

    def __fetch_metric_names(self):
         args = self.parser.parse_args(['labels', '__name__'])
         result = self.handler_map[args.command].handle(args)
         return result['data']

    def __fetch_label_names(self):
         args = self.parser.parse_args(['labels'])
         result = self.handler_map[args.command].handle(args)
         return result['data']

    def configure_autocompletion(self):
        metric_list = self.__fetch_metric_names()
        self.completer.update_metrics(metric_list)
        
        label_list =  self.__fetch_label_names()
        self.completer.update_labels(label_list)


