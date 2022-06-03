from tests.base_test import BaseTest

from crc import mail

from crc.services.user_file_service import UserFileService


class TestEmailAttachments(BaseTest):

    irb_code_1 = 'Study_App_Doc'
    irb_code_2 = 'Study_Protocol_Document'

    def setup_attachments(self):
        self.create_reference_document()

        workflow = self.create_workflow('email_script')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="something.png", content_type="text",
                                          binary_data=b'1234', irb_doc_code=self.irb_code_1)
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="another.png", content_type="text",
                                          binary_data=b'67890', irb_doc_code=self.irb_code_1)
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="anything.png", content_type="text",
                                          binary_data=b'5678', irb_doc_code=self.irb_code_2)
        return workflow, first_task

    def test_email_attachments_one_code(self):

        workflow, first_task = self.setup_attachments()

        form_data = {'subject': 'My Test Subject',
                     'recipients': 'user@example.com',
                     'doc_codes': self.irb_code_1
                     }
        with mail.record_messages() as outbox:
            self.complete_form(workflow, first_task, form_data)
            self.assertEqual(1, len(outbox))
            self.assertEqual(2, len(outbox[0].attachments))
            self.assertEqual('image/png', outbox[0].attachments[0].content_type)
            self.assertEqual('something.png', outbox[0].attachments[0].filename)
            self.assertEqual(b'1234', outbox[0].attachments[0].data)

    def test_email_attachments_list_of_codes(self):

        workflow, first_task = self.setup_attachments()

        form_data = {'subject': 'My Test Subject',
                     'recipients': 'user@example.com',
                     'doc_codes': [self.irb_code_1, self.irb_code_2]
                     }
        with mail.record_messages() as outbox:
            self.complete_form(workflow, first_task, form_data)
            self.assertEqual(1, len(outbox))
            self.assertEqual(3, len(outbox[0].attachments))

    def test_email_attachments_list_of_codes_with_empty_filters(self):

        workflow, first_task = self.setup_attachments()

        form_data = {'subject': 'My Test Subject',
                     'recipients': 'user@example.com',
                     'doc_codes': [(self.irb_code_1, []), (self.irb_code_2, [])]
                     }
        with mail.record_messages() as outbox:
            self.complete_form(workflow, first_task, form_data)
            self.assertEqual(1, len(outbox))
            self.assertEqual(3, len(outbox[0].attachments))

    def test_email_attachments_list_of_codes_with_filters(self):

        workflow, first_task = self.setup_attachments()

        doc_code_tuple_1 = (self.irb_code_1, ['another.png'])
        doc_code_tuple_2 = (self.irb_code_2, [])
        form_data = {'subject': 'My Test Subject',
                     'recipients': 'user@example.com',
                     'doc_codes': [doc_code_tuple_1, doc_code_tuple_2]
                     }

        with mail.record_messages() as outbox:
            self.complete_form(workflow, first_task, form_data)
            self.assertEqual(1, len(outbox))
            # We should only get 2 files because we filtered one out
            self.assertEqual(2, len(outbox[0].attachments))

    def test_email_attachments_list_of_codes_some_with_filters(self):
        workflow, first_task = self.setup_attachments()

        doc_code_tuple = (self.irb_code_1, ['another.png'])
        form_data = {'subject': 'My Test Subject',
                     'recipients': 'user@example.com',
                     'doc_codes': [doc_code_tuple, self.irb_code_2]
                     }

        with mail.record_messages() as outbox:
            self.complete_form(workflow, first_task, form_data)
            self.assertEqual(1, len(outbox))
            # We should only get 2 files because we filtered one out
            self.assertEqual(2, len(outbox[0].attachments))

