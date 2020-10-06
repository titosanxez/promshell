from abc import ABC, abstractmethod
from enum import Enum
import json

from promshell.handler import CommandHandler
from .rest_builder import Query, Series, Labels

HTTP_REQUEST_HEADERS = {
    "Content-type": "application/x-www-form-urlencoded"
}


# Interface for command handling
class AbstractGetHandler(CommandHandler):
    def __init__(self, http_conn):
        self.http_conn = http_conn

    @abstractmethod
    def build_request_info(self, parsed_args):
        NotImplemented 

    def handle(self, command_args):
        request_info = self.build_request_info(command_args)
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

class GetQuery(AbstractGetHandler):
    def __init__(self, http_conn):
        super().__init__(http_conn)

    def build_request_info(self, command_spec):
        return Query.build(command_spec)

    def help(self):
        return 'Obtains an instant query or range query'

    def setup_argparser(self, parser):
        Query.setup_argparser(parser)
        

    
class GetSeries(AbstractGetHandler):
    def __init__(self, http_conn):
        super().__init__(http_conn)
        
    def build_request_info(self, command_args):
        return Series.build(command_args)

    def help(self):
        return 'Obtains Series data for the specified metric expression'
    
    def setup_argparser(self, parser):
        Series.setup_argparser(parser)

class GetLabels(AbstractGetHandler):
    def __init__(self, http_conn):
        super().__init__(http_conn)

    def help(self):
        return 'Obtains label information'
        
    def build_request_info(self, parsed_args):        
        return Labels.build(parsed_args)

    def setup_argparser(self, parser):
        Labels.setup_argparser(parser)


class GetInstance(AbstractGetHandler):
    def __init__(self, http_conn):
        super().__init__(http_conn)

    def help(self):
        return 'Obtains Topic instance information'
    
    def setup_argparser(self, parser):
        Instance.setup_argparser(parser)

    def build_request_info(self, parsed_args):
        return Instance.build(parsed_args)