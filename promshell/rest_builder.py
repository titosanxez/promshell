import argparse


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

        Example:

            ..code::

                http_request_total

            ..code::

                http_request_total time=2015-07-01T20:11:00.781Z

            ..code::

                http_request_total start=2015-07-01T20:11:00.781Z,end=2015-07-01T20:11:00.781Z,step=30s

    """

    ARG_SPEC = {
        'expression': dict(
            help='Prometheus query expression',
            nargs='?',
            metavar='<query_exp>'),
        'instant': dict(
            flags=['-i', '--instant'],
            help='concrete instant timestamp, for instant queries',
            nargs='?',
            metavar='<timestamp>'),
        'range': dict(
            flags=['-r', '--range'],
            help='time period specified as start_t,end_t, for range queries',
            nargs='?',
            metavar='<start_t,end_t>'),
        'step': dict(
            flags=['-s', '--step'],
            help='query resolution format, for range queries.',
            nargs='?'),
        'timeout': dict(
            flags=['-t', '--timeout'],
            help='Evaluation timeout. Optional.',
            nargs='?'),
    }

    @staticmethod
    def build(parsed_args: argparse.Namespace):
        request_info = HttpRequestInfo()

        request_info.method = 'POST'
        request_info.params = 'query=%s' % parsed_args.expression
        request_info.resource = '/api/v1/query'
        if parsed_args.instant:
            print(parsed_args)
            request_info.params += '&time=%s' % parsed_args.instant
        elif parsed_args.range:
            request_info.resource = '/api/v1/query_range'
            range_args = parsed_args.range.split(',')
            request_info.params += '&start=%s' % range_args[0]
            request_info.params += '&end=%s' % range_args[1]
            request_info.params += '&step=%s' % parsed_args.step

        if parsed_args.timeout:
            request_info.params += '&timeout=%s' % parsed_args.timeout

        return request_info


class Series:
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

    """

    OPERATORS = ['=', '=~', '!=', '!~']

    ARG_SPEC = {
        'metric': dict(
            help='metric name',
            nargs='?',
            metavar='<metric>'),
        'label_exp': dict(
            flags=['-l', '--label'],
            help='list of comma-separated <label>[op]<value> elements',
            nargs='?',
            metavar='<label_exp>'),
        'raw_params': dict(
            flags=['-r', '--raw-params'],
            help='raw REST parameters',
            nargs='?',
            metavar='<raw_params>')
    }

    @staticmethod
    def build(parsed_args: argparse.Namespace):
        request_info = HttpRequestInfo()
        if not parsed_args.metric and not parsed_args.raw_params:
            return request_info

        if parsed_args.raw_params:
            request_info.params = parsed_args.raw_params
        else:
            request_info.params = 'match[]=%s' % parsed_args.metric
            if parsed_args.label_exp:
                request_info.params += \
                    '{%s}' % Series.__label_expression(parsed_args.label_exp)

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
    """

    ARG_SPEC = {
        'label': dict(
            help='label name',
            nargs='?',
            metavar='<label_name>'),
        'range': dict(
            flags=['-r', '--range'],
            help='time period specified as <start_t>[,<end_t>]',
            nargs='?',
            metavar='<start_t,end_t>')
    }

    @staticmethod
    def build(parsed_args: argparse.Namespace):
        request_info = HttpRequestInfo()
        request_info.method = 'GET'
        if parsed_args.label:
            request_info.resource = '/api/v1/label/%s/values' % parsed_args.label
        else:
            request_info.resource = '/api/v1/labels'
            request_info.params = None

        if parsed_args.range:
            range_args = parsed_args.range.split(',')
            request_info.params += '&start=%s' % range_args[0]
            if len(range_args) == 2:
                request_info.params += '&end=%s' % range_args[1]
            
        return request_info




