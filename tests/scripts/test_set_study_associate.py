from tests.base_test import BaseTest

from crc import session, db
from crc.models.study import StudyModel, StudyAssociated
from crc.scripts.update_study_associate import UpdateStudyAssociates


class TestSetStudyAssociate(BaseTest):

    def setUp(self):
        self.workflow = self.create_workflow('study_associates_validation')
        self.workflow_api = self.get_workflow_api(self.workflow)
        self.task = self.workflow_api.next_task
        self.study_id = self.workflow.study_id
        self.update_script = UpdateStudyAssociates()

    def test_update_study_associate(self):
        self.update_script.do_task(self.task, self.study_id, self.workflow.id, uid='dhf8r', role='PI')
        associates = db.session.query(StudyAssociated).filter(StudyAssociated.study_id == self.study_id).all()
        self.assertEqual(1, len(associates))

    def test_no_duplicate_associates(self):
        self.update_script.do_task(self.task, self.study_id, self.workflow.id, uid='dhf8r', role='PI')
        self.update_script.do_task(self.task, self.study_id, self.workflow.id, uid='dhf8r', role='PI')
        self.update_script.do_task(self.task, self.study_id, self.workflow.id, uid='dhf8r', role='PI')
        associates = db.session.query(StudyAssociated).filter(StudyAssociated.study_id == self.study_id).all()
        self.assertEqual(1, len(associates))

    def test_same_uid_in_two_rules(self):
        self.update_script.do_task(self.task, self.study_id, self.workflow.id, uid='dhf8r', role='PI')
        self.update_script.do_task(self.task, self.study_id, self.workflow.id, uid='dhf8r', role='DC')
        associates = db.session.query(StudyAssociated).filter(StudyAssociated.study_id == self.study_id).all()
        self.assertEqual(2, len(associates))
