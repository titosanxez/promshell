import unittest
from tests.test_completion import TestArgCompleter
from tests.test_arguments import TestArgumentDesc

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestArgCompleter))
    suite.addTest(unittest.makeSuite(TestArgumentDesc))
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())