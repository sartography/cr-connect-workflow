from tests.base_test import BaseTest
from crc import session
from crc.models.data_store import DataStoreModel
from crc.models.file import FileModel, FileType
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.services.workflow_service import WorkflowService
from flask import g

import time


class TestDataStoreValidation(BaseTest):

    @staticmethod
    def add_test_file():
        file_model = FileModel(
            name='my_test_file',
            type=FileType.pdf,
            content_type='application/pdf'
        )
        session.add(file_model)
        session.commit()
        file_id = session.query(FileModel.id).filter(FileModel.name == 'my_test_file').scalar()
        return file_id

    @staticmethod
    def add_previous_data_stores(user, study, spec_model, file_id):
        dsm = DataStoreModel(
            key='previous_study_data_key',
            workflow_id=None,
            study_id=study.id,
            task_spec=None,
            spec_id=spec_model.id,
            user_id=None,
            file_id=None,
            value='previous_study_data_value'

        )
        session.add(dsm)
        dsm = DataStoreModel(
            key='previous_user_data_key',
            workflow_id=None,
            study_id=None,
            task_spec=None,
            spec_id=spec_model.id,
            user_id=user.uid,
            file_id=None,
            value='previous_user_data_value'
        )
        session.add(dsm)
        dsm = DataStoreModel(
            key='previous_file_data_key',
            workflow_id=None,
            study_id=None,
            task_spec=None,
            spec_id=spec_model.id,
            user_id=None,
            file_id=file_id,
            value='previous_file_data_value'
        )
        session.add(dsm)

        session.commit()

    @staticmethod
    def add_multiple_records(file_id):
        dsm = DataStoreModel(
            key='some_key',
            workflow_id=None,
            study_id=None,
            task_spec=None,
            spec_id=None,
            user_id=None,
            file_id=file_id,
            value='previous_file_data_value_1'
        )
        session.add(dsm)
        session.commit()
        time.sleep(1)

        dsm = DataStoreModel(
            key='some_key',
            workflow_id=None,
            study_id=None,
            task_spec=None,
            spec_id=None,
            user_id=None,
            file_id=file_id,
            value='previous_file_data_value_2'
        )
        session.add(dsm)
        session.commit()
        time.sleep(1)

        dsm = DataStoreModel(
            key='some_key',
            workflow_id=None,
            study_id=None,
            task_spec=None,
            spec_id=None,
            user_id=None,
            file_id=file_id,
            value='previous_file_data_value_3'
        )
        session.add(dsm)
        session.commit()

    def run_data_store_set(self, form_data):
        workflow = self.create_workflow('data_store_set')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        self.complete_form(workflow, task, form_data)
        result = session.query(DataStoreModel).all()
        return result

    def test_data_store_validation(self):
        # add_studies also adds test users
        self.add_studies()
        user = session.query(UserModel).first()
        g.user = user
        study = session.query(StudyModel).first()
        spec_model = self.load_test_spec('data_store_validation')
        file_id = self.add_test_file()
        self.add_previous_data_stores(user, study, spec_model, file_id)

        result = WorkflowService.test_spec(spec_model.id, validate_study_id=study.id)
        self.assertIn('previous_study_data_value', result)
        self.assertEqual('previous_study_data_value', result['previous_study_data_value'])
        self.assertIn('previous_file_data_value', result)
        self.assertEqual('previous_file_data_value', result['previous_file_data_value'])
        self.assertIn('previous_user_data_value', result)
        self.assertEqual('previous_user_data_value', result['previous_user_data_value'])

        self.assertIn('study_data_value', result)
        self.assertEqual('study_data_value', result['study_data_value'])
        self.assertIn('file_data_value', result)
        self.assertEqual('file_data_value', result['file_data_value'])
        self.assertIn('user_data_value', result)
        self.assertEqual('user_data_value', result['user_data_value'])

        self.assertIn('bad_study_data_value', result)
        self.assertEqual('bad_study_data_value', result['bad_study_data_value'])
        self.assertIn('bad_file_data_value', result)
        self.assertEqual('bad_file_data_value', result['bad_file_data_value'])
        self.assertIn('bad_user_data_value', result)
        self.assertEqual('bad_user_data_value', result['bad_user_data_value'])

    def test_set_reset_data_store(self):
        """Add records to the data store,
           then set new values for those records.
           Assert that we don't create new records.
           Assert that we have the new values"""
        file_id = self.add_test_file()

        form_data = {'key': 'my_key', 'value': 'my_value', 'file_id': file_id}
        result = self.run_data_store_set(form_data)

        self.assertEqual(3, len(result))
        for record in result:
            self.assertEqual('my_value', record.value)

        form_data = {'key': 'my_key', 'value': 'my_new_value', 'file_id': file_id}
        result = self.run_data_store_set(form_data)

        self.assertEqual(3, len(result))
        for record in result:
            self.assertEqual('my_new_value', record.value)

    def test_reset_datastore_different_workflow(self):
        """Add records to the data store,
           then set new values for those records from a different workflow.
           Assert that we don't create new records.
           Assert that we have the new values"""
        file_id = self.add_test_file()

        form_data = {'key': 'some_key', 'value': 'some_value', 'file_id': file_id}
        result = self.run_data_store_set(form_data)

        self.assertEqual(3, len(result))
        for record in result:
            self.assertEqual('some_value', record.value)

        workflow = self.create_workflow('data_store_set_2')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        form_data = {'key': 'some_key', 'value': 'some_new_value', 'file_id': file_id}
        self.complete_form(workflow, task, form_data)

        result = session.query(DataStoreModel).all()
        self.assertEqual(3, len(result))
        for record in result:
            self.assertEqual('some_new_value', record.value)

    def test_delete_extra_records(self):
        """We had a bug where we created new records instead of updating existing records
           This ensures we remove 'extra' records"""
        file_id = self.add_test_file()
        self.add_multiple_records(file_id)

        result = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id).all()
        self.assertEqual(3, len(result))
        previous_values = ['previous_file_data_value_1', 'previous_file_data_value_2', 'previous_file_data_value_3']
        for record in result:
            self.assertIn(record.value, previous_values)

        form_data = {'key': 'some_key', 'value': 'some_value', 'file_id': file_id}
        result = self.run_data_store_set(form_data)

        self.assertEqual(3, len(result))
        for record in result:
            self.assertEqual('some_value', record.value)

    def test_delete_record_on_none_or_empty_string(self):
        """If we set a data store with None or an empty string,
           assert that we delete the record."""
        file_id = self.add_test_file()

        # Test for empty string
        form_data = {'key': 'my_key', 'value': 'my_value', 'file_id': file_id}
        result = self.run_data_store_set(form_data)

        self.assertEqual(3, len(result))
        for record in result:
            self.assertEqual('my_value', record.value)

        workflow = self.create_workflow('data_store_set')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        re_form_data = {'key': 'my_key', 'value': '', 'file_id': file_id}
        self.complete_form(workflow, task, re_form_data)

        result = session.query(DataStoreModel).all()
        self.assertEqual(0, len(result))

        # Test for None
        form_data = {'key': 'my_second_key', 'value': 'my_second_value', 'file_id': file_id}
        result = self.run_data_store_set(form_data)

        self.assertEqual(3, len(result))
        for record in result:
            self.assertEqual('my_second_value', record.value)

        workflow = self.create_workflow('data_store_set')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        # The workflow turns the string 'None' into the value None
        re_form_data = {'key': 'my_second_key', 'value': 'None', 'file_id': file_id}
        self.complete_form(workflow, task, re_form_data)

        result = session.query(DataStoreModel).all()
        self.assertEqual(0, len(result))

