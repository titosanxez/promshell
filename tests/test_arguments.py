import enum
import unittest
import argparse

import promshell.arguments as arguments
from promshell.arguments import ArgDescriptor

class TestArgumentDesc(unittest.TestCase):

    def test_setup_parser(self):
        parser = argparse.ArgumentParser()

        arguments.add_parser_arguments(parser, arguments.QUERY_ARGDESC)
        args = parser.parse_args('exp -i val1 -r val2 -s val3 -t val4'.split())
        self.assertEqual('exp', args.exp)
        self.assertEqual('val1', args.instant)
        self.assertEqual('val2', args.range)
        self.assertEqual('val3', args.step)
        self.assertEqual('val4', args.timeout)




