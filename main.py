from enum import Enum

from promshell.shell import Shell, ShellProperty
from promshell.prometheus import rest_builder, handlers


class PrometheusAction(Enum):
    QUERY = "query"
    SERIES = "series"
    LABELS = "labels"


if __name__ == "__main__":
    # __package__ = 'promshell'
    property = ShellProperty()

    property.prompt_name = "promshell"
    property.address = "localhost:9090"
    promshell = Shell(property.prompt_name)

    factory = handlers.HandlerFactory(
        server_address=property.address)
    factory.fetch()

    promshell.register_handler(
        PrometheusAction.QUERY.value,
        factory.handler(handlers.HandlerFactory.QUERY),
        arguments=rest_builder.Query.ARG_SPEC,
        help='Obtain an instant query or range query')
    promshell.register_handler(
        PrometheusAction.SERIES.value,
        factory.handler(handlers.HandlerFactory.SERIES),
        arguments=rest_builder.Series.ARG_SPEC,
        help='Obtain series data for a specified metric and label expression')
    promshell.register_handler(
        PrometheusAction.LABELS.value,
        factory.handler(handlers.HandlerFactory.LABELS),
        arguments=rest_builder.Labels.ARG_SPEC,
        help='Obtain label information')

    promshell.run()