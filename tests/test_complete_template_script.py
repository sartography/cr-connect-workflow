import unittest
import copy

from docxtpl import Listing

from crc.scripts.complete_template import CompleteTemplate


class TestCompleteTemplate(unittest.TestCase):

    def test_rich_text_update(self):
        script = CompleteTemplate()
        data = {"name": "Dan"}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertEqual(data, data_copy)

    def test_rich_text_update_new_line(self):
        script = CompleteTemplate()
        data = {"name": "Dan\n Funk"}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertNotEqual(data, data_copy)
        self.assertIsInstance(data_copy["name"], Listing)

    def test_rich_text_nested_new_line(self):
        script = CompleteTemplate()
        data = {"names": [{"name": "Dan\n Funk"}]}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertNotEqual(data, data_copy)
        self.assertIsInstance(data_copy["names"][0]["name"], Listing)
