import unittest

from tests.BaseTest import BaseTest


class TestWorkflow(BaseTest, unittest.TestCase):

    def test_truthyness(self):
        self.assertTrue(True)

    def test_