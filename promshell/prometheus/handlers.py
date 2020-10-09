from abc import ABC, abstractmethod
import json
import http.client
from typing import List, Iterable
from argparse import Namespace

from prompt_toolkit.completion import Completion, WordCompleter

from promshell.shell import CommandHandler
from promshell.completion import CompletionContext, KeyValueCompleter
from .rest_builder import Query, Series, Labels, HttpRequestInfo

HTTP_REQUEST_HEADERS = {
    "Content-type": "application/x-www-form-urlencoded"
}


def handle_request(
        http_conn: http.client.HTTPConnection,
        request_info: HttpRequestInfo) -> dict:
    http_conn.request(
        request_info.method,
        request_info.resource,
        request_info.params,
        HTTP_REQUEST_HEADERS)
    response = http_conn.getresponse()
    response_string = response.read().decode('utf-8')
    if response.getheader("Content-Type") == "application/json":
        return json.loads(response_string)
    else:
        return dict(result=response_string)


class HandlerContext:
    def __init__(self, http_conn):
        self.http_conn = http_conn
        self.metrics = []
        self.labels = []

    def handle_request(self, request_info: HttpRequestInfo) -> dict:
        self.http_conn.request(
            request_info.method,
            request_info.resource,
            request_info.params,
            HTTP_REQUEST_HEADERS)
        response = self.http_conn.getresponse()
        response_string = response.read().decode('utf-8')
        if response.getheader("Content-Type") == "application/json":
            return json.loads(response_string)
        else:
            return dict(result=response_string)


# Interface for command handling
class AbstractGetHandler(CommandHandler):
    def __init__(self, context: HandlerContext):
        self.context = context

    @abstractmethod
    def build_request_info(self, parsed_args):
        NotImplemented

    def handle(self, command_args) -> dict:
        request_info = self.build_request_info(command_args)
        return self.context.handle_request(request_info)

    def complete_word_for_choices(
            self,
            context: HandlerContext,
            choices: List[str],
            style: str = None) -> Iterable[Completion]:
        word_completer = WordCompleter(choices)
        for completion in word_completer.get_completions(context.document, context.event):
            yield Completion(
                text=completion.text,
                start_position=completion.start_position,
                style=style)


class GetQuery(AbstractGetHandler):
    def __init__(self, context: HandlerContext):
        super().__init__(context)

    def build_request_info(self, command_spec):
        return Query.build(command_spec)

    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        if context.arg_descriptor.name == 'expression' and self.context.metrics:
            choices = self.context.metrics
            color = 'fg:ansiblue'
        else:
            choices = [context.arg_descriptor.metavar]
            color = 'fg:ansired'
        return super().complete_word_for_choices(context, choices, color)


class GetSeries(AbstractGetHandler):
    def __init__(self, context: HandlerContext):
        super().__init__(context)

    def build_request_info(self, command_args):
        return Series.build(command_args)

    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        if context.arg_descriptor.name == 'metric' and self.context.metrics:
            choices = self.context.metrics
            color = 'fg:ansiblue'
        elif context.arg_descriptor.name == 'label_exp' and self.context.labels:
            color = 'fg:ansiblue'
            return KeyValueCompleter(
                self.context.labels,
                Series.OPERATORS).get_completions(context)
        else:
            choices = [context.arg_descriptor.metavar]
            color = 'fg:ansired'

        return super().complete_word_for_choices(context, choices, color)


class GetLabels(AbstractGetHandler):
    def __init__(self, context: HandlerContext):
        super().__init__(context)

    def build_request_info(self, parsed_args):
        return Labels.build(parsed_args)

    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        if context.arg_descriptor.name == 'label' and self.context.labels:
            choices = self.context.labels
            color = 'fg:ansiblue'
        else:
            choices = [context.arg_descriptor.metavar]
            color = 'fg:ansired'

        return super().get_word_completions_for_choices(context, choices, color)


# class FetchMetricsAndLabels(CommandHandler):
#     def __init__(self, http_conn):
#         self.http_conn = http_conn
#         self.metrics = []
#         self.labels = []
#
#     def handle(self, command_args) -> str:
#         self.fetch()
#         return "{'result': 'Metrics and Labels fetched OK'}"
#
#     def fetch(self):
#         # Fetch metric names
#         result = handle_request(
#             self.http_conn,
#             Labels.build(Namespace(labels='__name__')))
#         self.metrics = result['data']
#
#         # Fetch label names
#         result = handle_request(
#             self.http_conn,
#             Labels.build(Namespace(labels='')))
#         self.labels = result['data']

SERVER_ADDRESS_DEFAULT = 'localhost:9090'


class HandlerFactory:
    QUERY = GetQuery.__name__
    SERIES = GetSeries.__name__
    LABELS = GetLabels.__name__
    FETCH = 'HandlerFactory.FETCH'
    CONNECT = 'HandlerFactory.CONNECT'

    def __init__(self, server_address: str):
        self.http_connection: http.client.HTTPConnection = None
        if server_address:
            self.http_connection = http.client.HTTPConnection(server_address)
            self.http_connection.connect()
        self.context = HandlerContext(self.http_connection)

        # initialize handlers
        self.__handlers = {
            HandlerFactory.QUERY: GetQuery(self.context),
            HandlerFactory.SERIES: GetSeries(self.context),
            HandlerFactory.LABELS: GetLabels(self.context),
            HandlerFactory.FETCH: self.FetchHandler(self),
            HandlerFactory.CONNECT: self.ConnectHandler(self)
        }

    def handler(self, name: str) -> CommandHandler:
        return self.__handlers[name]

    # Fetch: CommandHandler implementation
    def handle(self, command_args) -> dict:
        self.fetch()
        return dict(result='Metrics and Labels fetched OK')

    def fetch(self):
        namespace = Namespace(label=None, range=None)
        # Fetch metric names
        namespace.label = '__name__'
        result = self.handler(HandlerFactory.LABELS).handle(namespace)
        self.context.metrics = result['data']

        # Fetch label names
        namespace.label = None
        result = self.handler(HandlerFactory.LABELS).handle(namespace)
        self.context.labels = result['data']

    #
    # Builtin Handlers
    #
    class FetchHandler(CommandHandler):
        ARG_SPEC = {}

        def __init__(self, factory):
            self.factory: HandlerFactory = factory

        def handle(self, command_args) -> dict:
            self.factory.fetch()
            return dict(result='Metrics and labels fetched OK')

    class ConnectHandler(CommandHandler):
        ARG_SPEC = {
            'address': dict(
                help='Prometheus server address',
                nargs='?',
                metavar='<server:port>',
                default=SERVER_ADDRESS_DEFAULT),
            'timeout': dict(
                flags=['-t', '--timeout'],
                help='connection timeout',
                nargs='?',
                metavar='<timeout>',
                type=int),
        }

        def __init__(self, factory):
            self.factory: HandlerFactory = factory

        def handle(self, command_args) -> dict:
            if command_args.address:
                server_address = command_args.address
            else:
                server_address = SERVER_ADDRESS_DEFAULT

            if command_args.timeout:
                timeout = command_args.timeout
            else:
                timeout = None

            current_address = \
                self.factory.http_connection.host \
                + '%s' % self.factory.http_connection.port
            if current_address != server_address:
                self.factory.http_connection = http.client.HTTPConnection(
                    server_address,
                    timeout=timeout)
                self.factory.http_connection.connect()
                return dict(
                    result='Connection established to: %s'
                           % command_args.address)
            return dict()
