import unittest

from tests.BaseTest import BaseTest


class TestWorkflow(BaseTest, unittest.TestCase):

    def test_truthyness(self):
        self.assertTrue(True)

    def test_404(self):
        response = self.app.get('/some/endpoint')
        self.assertEquals(404, response.status_code)

    def test_all_workflows(self):
        response = self.app.get('/v1.0/workflows')
        response_data = response.json
        self.assertEqual('Full IRB Board Review',response_data[0]['name'])