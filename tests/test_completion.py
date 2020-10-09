# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.
import enum
import unittest

from prompt_toolkit.document import Document
from promshell.prometheus import ArgDescription, OptionKind
from shell.completion import ArgumentCompleter

class TestArgCompleter(unittest.TestCase):

    ARG_DESCRIPTION = [
        ArgDescription(
                kind=OptionKind.POSITIONAL,
                name ='<pos1>',
                value=[]),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name ='-o1',
                value=['val1', 'val2']),
        ArgDescription(
                kind=OptionKind.SINGLE,
                name ='-o2',
                value=['<o2_value>'])
    ]

    class CaseKind(enum.IntEnum):
        DASH_ONLY = 0
        DASH_ONLY_SPACE = 1
        SINGLE_OPTION = 2
        SINGLE_OPTION_W_SPACE = 3
        SINGLE_OPTION_W_VALUE = 4
        SINGLE_OPTION_W_VALUE_AND_SPACE = 5
        SINGLE_OPTION_W_VALUE_W_POSITIONAL = 6
        SINGLE_OPTION_W_VALUE_W_POSITIONAL_AND_SPACE = 7
        ONE_POSITIONAL = 8
        ONE_POSITIONAL_AND_SPACE = 9
        POSITIONAL_W_OPTION = 10
        POSITIONAL_W_OPTION_AND_SPACE = 11
        POSITIONAL_W_OPTION_W_VALUE = 12
        POSITIONAL_W_OPTION_W_VALUE_AND_SPACE = 13
        TWO_OPTIONS = 14
        TWO_OPTIONS_AND_SPACE = 15
        TWO_OPTIONS_W_VALUE = 16
        TWO_OPTIONS_W_VALUE_AND_SPACE = 17

    TEST_CASES = [
        dict(line='-', expected=['<pos1>', '-o1', '-o2']), #DASH_ONLY
        dict(line='- ', expected=['-o1', '-o2']), #DASH_ONLY_SPACE
        dict(line='-o1', expected=['<pos1>', '-o1', '-o2']), #SINGLE_OPTION
        dict(line='-o1 ', expected=ARG_DESCRIPTION[1].choices), #3INGLE_OPTION_W_SPACE
        dict(line='-o1 value', expected=['val1', 'val2']), #SINGLE_OPTION_W_VALUE
        dict(line='-o1 value ', expected=['<pos1>', '-o2']), #SINGLE_OPTION_W_VALUE_AND_SPACE
        dict(line='-o1 value pos1', expected=['<pos1>', '-o2']), #SINGLE_OPTION_W_VALUE_W_POSITIONAL
        dict(line='-o1 value pos1 ', expected=['-o2']),  #SINGLE_OPTION_W_VALUE_W_POSITIONAL_AND_SPACE
        dict(line='pos1', expected=['<pos1>', '-o1', '-o2']),  # ONE_POSITIONAL
        dict(line='pos1 ', expected=['-o1', '-o2']),  #ONE_POSITIONAL_AND_SPACE
        dict(line='pos1 -o1', expected=['-o1', '-o2']),  # POSITIONAL_W_OPTION
        dict(line='pos1 -o1 ', expected=ARG_DESCRIPTION[1].choices),  # POSITIONAL_W_OPTION_AND_SPACE
        dict(line='pos1 -o1 value', expected=ARG_DESCRIPTION[1].choices),  # POSITIONAL_W_OPTION_W_VALUE
        dict(line='pos1 -o1 value ', expected=['-o2']),  # POSITIONAL_W_OPTION_W_VALUE_AND_SPACE
        dict(line='-o1 -o2', expected=ARG_DESCRIPTION[1].choices),  # TWO_OPTIONS
        dict(line='-o1 -o2 ', expected=ARG_DESCRIPTION[2].choices),  # TWO_OPTIONS_AND_SPACE
        dict(line='-o1 -o2 val', expected=ARG_DESCRIPTION[2].choices),  # TWO_OPTIONS_W_VALUE
        dict(line='-o1 -o2 val ', expected=['<pos1>']),  # TWO_OPTIONS_W_VALUE_AND_SPACE
    ]
    
    #    def setUp(self):
    #        self.foo = Tests()
    

    #def tearDown(self):
    #    self.foo.dispose()
    #    self.foo = None

    def check_completions(self, arg_description, test_case):
        expected_completions = test_case['expected'].copy()
        expected_completions.append('')
        completer = ArgumentCompleter(arg_description)
        document = Document(test_case['line'], cursor_position=0)

        completed = []
        for item in completer.get_completions(document, None):
            completed.append(item.text)

        self.assertEqual(expected_completions, completed)

    def test_dash_only(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.DASH_ONLY.value])

    def test_dash_only_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.DASH_ONLY_SPACE.value])

    def test_single_option(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.SINGLE_OPTION.value])

    def test_single_option_with_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.SINGLE_OPTION_W_SPACE.value])
        
    def test_single_option_with_value(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.SINGLE_OPTION_W_VALUE.value])

    def test_single_option_with_value_and_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.SINGLE_OPTION_W_VALUE_AND_SPACE.value])

    def test_single_option_with_value_with_pos(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.SINGLE_OPTION_W_VALUE_W_POSITIONAL.value])

    def test_one_positional(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.ONE_POSITIONAL.value])

    def test_one_positional_and_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.ONE_POSITIONAL_AND_SPACE.value])

    def test_one_positional_with_option(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.POSITIONAL_W_OPTION.value])

    def test_one_positional_with_option_and_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.POSITIONAL_W_OPTION_AND_SPACE.value])

    def test_one_positional_with_option_with_value(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.POSITIONAL_W_OPTION_W_VALUE.value])

    def test_one_positional_with_option_with_value_and_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.POSITIONAL_W_OPTION_W_VALUE_AND_SPACE.value])

    def test_two_options(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.TWO_OPTIONS.value])

    def test_two_options_and_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.TWO_OPTIONS_AND_SPACE.value])

    def test_two_options_with_value(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.TWO_OPTIONS_W_VALUE.value])

    def test_two_options_with_value_and_space(self):
        self.check_completions(
            TestArgCompleter.ARG_DESCRIPTION,
            TestArgCompleter.TEST_CASES[TestArgCompleter.CaseKind.TWO_OPTIONS_W_VALUE_AND_SPACE.value])


