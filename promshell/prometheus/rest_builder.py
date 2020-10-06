from enum import Enum
import argparse

class OptionKind(Enum):
    FLAG = 0
    SINGLE = 1
    POSITIONAL = 2
    KEYVALUE_LIST = 3


class ArgDescription:
    def __init__(self):
        self.kind = OptionKind.FLAG
        self.name = None
        self.value = None

    def __init__(self, **kwargs):
        self.kind = OptionKind.FLAG
        self.name = None
        self.value = []
        for key,value in kwargs.items():
            setattr(self, key, value)

    def is_positional(self):
        return self.kind == OptionKind.POSITIONAL

    def is_single(self):
        return self.kind == OptionKind.SINGLE

    def is_flag(self):
        return self.kind == OptionKind.FLAG

    def is_keyvalue(self):
        return self.kind == OptionKind.KEYVALUE_LIST

class HttpRequestInfo:
    """Encapsulation of a Prometheus HTTP Request elements."""

    def __init__(self):
        """Default constructor that obtains all the available series"""
        self.method = 'POST'
        self.resource = '/api/v1/series'
        self.params = 'match[]={__name__=~\'.*\'}'

class Query:
    """
    The command spec follows the following format:

           ..code::

                [query_exp] [-i <time>] | [-r <start_t>,<end_t> -s <step>] [-t <time>]

            where:

            * query_exp: Prometheus query expression.
            * -i: concrete timestamp, for instant queries.
            * -r: start,end timestamps, for range queries.
            * -s: query resolution format, for range queries.
            * -t Evaluation timeout. Optional.
    """

    ARG_DESCRIPTION = [
        ArgDescription(
                kind=OptionKind.POSITIONAL,
                name ='<exp>',
                value=[]),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name ='-i',
                value=['<instant_timestamp>']),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name ='-r',
                value=['<start_t>,<end_t>']),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name ='-s',
                value=['<step>']),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name ='-t',
                value=['<timeout>'])
    ]

    def setup_argparser(parser):
        """Sets up the command parser with the available options. See ARG_DESCRIPTION.

            The command spec follows the following format:

               ..code::

                    [query_exp] [-i <time>] | [-r <start_t>,<end_t> -s step<s>] [-t <time>]

                where:

                * query_exp: Prometheus query expression.
                * time: concrete timestamp, for instant queries.
                * start: start timestamp, for range queries.
                * end: end timestamp, for range requeries.
                * step: query resolution format, for range queries.
                * timeout= Evaluation timeout. Optional.

                Example:

                    ..code::

                        http_request_total

                    ..code::

                        http_request_total time=2015-07-01T20:11:00.781Z

                    ..code::

                        http_request_total start=2015-07-01T20:11:00.781Z,end=2015-07-01T20:11:00.781Z,step=30s


            :param command_spec: A list of strings representing the command
                specification
        """
        
        parser.add_argument(
            'exp',
            help='Prometheus query expression',
            nargs='?')
        parser.add_argument(
            '-i', '--instant',
            dest='instant',
            nargs='?',
            help='concrete instant timestamp, for instant queries')
        parser.add_argument(
            '-r', '--range',
            dest='range',
            nargs='?',
            help='time period specified as start_t,end_T, for range queries')
        parser.add_argument(
            '-s', '--step',
            dest='step',
            nargs='?',
            help='query resolution format, for range queries.')
        parser.add_argument(
            '-t', '--timeout',
            metavar='timeout',
            nargs='?',
            help=' Evaluation timeout. Optional.')

    def build(parsed_args):
        request_info = HttpRequestInfo()

        request_info.method = 'POST'
        request_info.params = 'query=%s' % parsed_args.exp
        request_info.resource = '/api/v1/query'
        if parsed_args.instant != None:
            print(parsed_args)
            request_info.params += '&time=%s' % parsed_args.instant
        elif parsed_args.range:
            request_info.resource = '/api/v1/query_range'
            range_args = parsed_args.range.split(',')
            request_info.params += '&start=%s' % range_args[0]
            request_info.params += '&end=%s' % range_args[1]
            request_info.params += '&step=%s' % parsed_args.step

        if parsed_args.timeout != None:
            request_info.params += '&timeout=%s' % parsed_args.timeout

        return request_info


class Series:

    OPERATORS = ['=', '=~', '!=', '!~']

    ARG_DESCRIPTION = [
        ArgDescription(
                kind=OptionKind.POSITIONAL,
                name ='<metric>',
                value=[]),
        ArgDescription(
                kind=OptionKind.KEYVALUE_LIST,
                name ='-l',
                value=['<label_exp>']),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name='-r',
                value=['<rawparams>'])
    ]

    def setup_argparser(parser):
        """Returns a request info object to obtain the specified set of series.

            The command spec follows the following format:

               ..code::

                    --raw raw_params | metric_name -l [label_expression]

                where:

                * raw_params: Raw HTTP POST series parameters
                * metric_name: name of the metric.
                * ``label_expression`` is a comma-separated list of label-value
                  pairs, expressed as a comparison using one of the available Promql
                  comparison operators. Optional.

                Example:

                    ..code::

                        http_request_total job=prometheus,instance=~'localhost*'

                    ..code::

                        -r match[]=http_request_total{job=prometheus,instance=~'localhost*'}


            :param command_spec: A list of strings representing the command
                specification

        """
        parser.add_argument(
            'metric',
            metavar='metric',
            nargs='?',
            help='metric name')
        parser.add_argument(
            '-l', '--label_exp',
            dest='labelexp',
            nargs='?',
            help='comma-separated list of label-value comparisons through a PromQL operator')
        parser.add_argument(
            '-r', '--raw',
            dest='rawparams',
            metavar='rawparams',
            nargs='?',
            help='Use a raw HTTP POST series parameters')

    def build(args):
        request_info = HttpRequestInfo()
        if (args.metric == None) and (args.rawparams == None):
            return request_info

        if args.rawparams != None:
            request_info.params = args.rawparams
        else:
            request_info.params = 'match[]=%s' % args.metric
            if args.labelexp != None:
                request_info.params += '{%s}' % Series.__label_expression(args.labelexp)

        return request_info

    def __label_expression(labels):
        label_list = labels.split(',')
        rest_label_exp = ''
        exp_elements = None
        for item in label_list:
            for op in Series.OPERATORS:
                exp_elements = list(item.partition(op))

                if exp_elements[1] == '':
                    continue

                if not exp_elements[2].startswith('\''):
                    exp_elements[2] = '\'%s\'' % exp_elements[2]
                    break

            # add expression for label item
            if rest_label_exp != '':
                rest_label_exp += ','
            rest_label_exp += exp_elements[0] + exp_elements[1] + exp_elements[2]

        return rest_label_exp
class Labels:

    ARG_DESCRIPTION = [
        ArgDescription(
                kind=OptionKind.POSITIONAL,
                name ='<label>',
                value=[]),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name ='-r',
                value=['<start_t>,<end_t>'])
    ]
    
    def setup_argparser(parser):
        """Returns a request info object to obtain label information

            The command spec follows the following format:

               ..code::

                    [label_name] [start_time[,end_time]]

                where:

                * label_name: Name of the label whose values are obtained. Optional.
                * Start timestmap in Prometheus format. Optional.
                * end timestmap in Prometheus format. Optional.

                Example:

                    ..code::

                        http_request_total

                    ..code::

                        http_request_total 2015-07-01T20:10:30.781Z,2015-07-01T20:11:00.781Z


            :param command_spec: A list of strings representing the command
                specification
        """
        parser.add_argument(
            'label',
            help='label name',
            nargs='?')
        parser.add_argument(
            '-r', '--range',
            dest='range',
            nargs='?',
            help='time period specified as start_t,[end_T]')

    def build(parsed_args):
        request_info = HttpRequestInfo()

        request_info.method = 'GET'
        if parsed_args.label == None:
            request_info.resource ='/api/v1/labels'
            request_info.params = None
        else:
            request_info.resource ='/api/v1/label/%s/values' % parsed_args.label

        if parsed_args.range != None:
            range_args = parsed_args.range.split(',')
            request_info.params += '&start=%s' % range_args[0]
            if len(range_args) == 2:
                request_info.params += '&end=%s' % range_args[1]
            
        return request_info


class Instance:

    def setup_argparser(parser):
        """Returns a request info object to obtain label information

            The command spec follows the following format:

               ..code::

                    [key_hash] | [-l label_pairs]

                where:

                * key_hash: key has value in hexadecimal
                * label_pairs: comma-separated list of name-value labels                


            :param command_spec: A list of strings representing the command
                specification
        """
        parser.add_argument(
            'key_hash',
            help='key has value as hexadecimal',
            nargs='?')
        parser.add_argument(
            '-l', '--labels',
            dest='labels',
            nargs='?',
            help='comma-separated list of name-value labels')


    def build(parsed_args):
        series_spec = ["instance_info"]
        label_exp = parsed_args.labels
        if parsed_args.key_hash != None:
            label_exp = 'key=\'%s\'' % parsed_args.key_hash

        series_args = argparse.Namespace(
                metric='instance_info',
                labelexp=label_exp,
                rawparams=None)
        return  Series.build(series_args)


