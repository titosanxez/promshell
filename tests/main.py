import unittest
from tests.test_completion import TestArgCompleter

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestArgCompleter))
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())