import argparse

from promshell.promshell import PromShell, program_name
import shell

if __name__ == "__main__":
    PARSER_CONFIG = {
        'prog': program_name(),
        'description': 'Interactive command-line interface to obtain information from Prometheus',
        'add_help': True
    }
    parser = argparse.ArgumentParser(**PARSER_CONFIG)
    shell.arguments.add_parser_arguments(
        parser,
        PromShell.ARG_SPEC
    )
    arguments = parser.parse_args()
    promshell = PromShell(**vars(arguments))
    promshell.run()
