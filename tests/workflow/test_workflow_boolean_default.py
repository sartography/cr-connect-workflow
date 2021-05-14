from tests.base_test import BaseTest


class TestBooleanDefault(BaseTest):

    def do_test(self, yes_no):
        workflow = self.create_workflow('boolean_default_value')
        workflow_api = self.get_workflow_api(workflow)
        set_default_task = workflow_api.next_task
        result = self.complete_form(workflow, set_default_task, {'yes_no': yes_no})
        return result

    def test_boolean_true_string(self):

        yes_no = 'True'
        result = self.do_test(yes_no)
        self.assertEqual(True, result.next_task.data['pick_one'])

    def test_boolean_true_string_lower(self):

        yes_no = 'true'
        result = self.do_test(yes_no)
        self.assertEqual(True, result.next_task.data['pick_one'])

    def test_boolean_t_string(self):

        yes_no = 'T'
        result = self.do_test(yes_no)
        self.assertEqual(True, result.next_task.data['pick_one'])

    def test_boolean_t_string_lower(self):

        yes_no = 't'
        result = self.do_test(yes_no)
        self.assertEqual(True, result.next_task.data['pick_one'])

    def test_boolean_true(self):

        yes_no = True
        result = self.do_test(yes_no)
        self.assertEqual(True, result.next_task.data['pick_one'])

    def test_boolean_false_string(self):

        yes_no = 'False'
        result = self.do_test(yes_no)
        self.assertEqual(False, result.next_task.data['pick_one'])

    def test_boolean_false_string_lower(self):

        yes_no = 'false'
        result = self.do_test(yes_no)
        self.assertEqual(False, result.next_task.data['pick_one'])

    def test_boolean_f_string(self):

        yes_no = 'F'
        result = self.do_test(yes_no)
        self.assertEqual(False, result.next_task.data['pick_one'])

    def test_boolean_f_string_lower(self):

        yes_no = 'f'
        result = self.do_test(yes_no)
        self.assertEqual(False, result.next_task.data['pick_one'])

    def test_boolean_false(self):

        yes_no = False
        result = self.do_test(yes_no)
        self.assertEqual(False, result.next_task.data['pick_one'])
