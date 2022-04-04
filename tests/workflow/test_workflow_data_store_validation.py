from tests.base_test import BaseTest
from crc import session
from crc.models.data_store import DataStoreModel
from crc.models.file import FileModel, FileType
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.services.workflow_service import WorkflowService
from flask import g


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
