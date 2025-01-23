from tests.base_test import BaseTest
from crc import app
from crc.models.ldap import LdapModel
from unittest.mock import patch
import random
import json


class TestSetPBAssociates(BaseTest):

    user_data = {'PI': ('Alice Thompson', 'ghg3qe'), 'SC_I': ('Brian Edwards', 'zxriuk'), 'DEPT_CH': ('Catherine Wilson', '80vn'),
                 'AS_C': ('Daniel Martinez', '676pe'), 'AS_C_2': ('Emily Johnson', 'tl5h'), 'SI': ('Franklin Harris', 'y4suzz'),
                 'SI_2': ('Georgia Clarke', 'jci60'), 'SI_3': ('Henry Robinson', 'ouvhr'), 'IRBC': ('Isabel Carter', 'dxigow')}

    def get_associated_users(self, study_id):
        rv = self.app.get(f'/v1.0/study/{study_id}/associates',
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        return json.loads(rv.get_data(as_text=True))

    def get_mock_investigators(self):
        investigators = {}
        for (role, (name, uid)) in self.user_data.items():
            investigators[role] = {'code': role, 'label': role, 'display': 'Always', 'unique': 'Yes', 'user_id': uid,
                                   'uid': uid, 'display_name': name, 'given_name': name.split()[0],
                                   'email_address': f'{uid}@virginia.edu',
                                   'telephone_number': ''.join([random.choice('0123456789') for _ in range(10)]),
                                   'title': 'E0:Staff', 'department': 'EN:Engineering', 'affiliation': 'staff',
                                   'sponsor_type': '', 'date_cached': '2024-04-11T19:24:35.980782-04:00'}
        return investigators

    def create_additional_users(self):
        user_data = self.user_data
        for key, (name, uid) in user_data.items():
            ldap_model = LdapModel(uid=uid,
                                   display_name=name,
                                   given_name=name.split()[0],
                                   email_address=f'{uid}@virginia.edu',
                                   telephone_number=''.join([random.choice('0123456789') for i in range(10)]),
                                   title='E0:Staff',
                                   department='EN:Engineering',
                                   affiliation='staff',
                                   sponsor_type='')
            self.add_user(ldap_model)

    @patch('crc.services.study_service.StudyService.get_investigators')  # mock_investigators
    def test_set_pb_associates(self, mock_investigators):
        app.config['PB_ENABLED'] = True
        self.add_users()  # adds users in test ldap
        self.create_additional_users()

        mock_investigators.return_value.ok = True
        mock_investigators.return_value = self.get_mock_investigators()

        workflow = self.create_workflow('set_pb_associates')

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.name == 'Activity_Review_Before_Load_IRB'
        assert task.data == {}

        associated_users = self.get_associated_users(workflow_api.study_id)
        assert len(associated_users) == 1

        self.complete_form(workflow, task, {})

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.name == 'Activity_Review_Before_Add_Additional'
        assert len(task.data) == 23

        for assoc_type in ['pi', 'dc', 'pcs', 'subs', 'subx']:
            assert assoc_type in task.data

        assert len(task.data['pi']) == 14
        assert len(task.data['dc']) == 14
        assert len(task.data['pcs']) == 4
        assert len(task.data['subs']) == 3
        assert len(task.data['subx']) == 0

        self.complete_form(workflow, task, {})

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.name == 'Activity_Add_Additional_Personnel'
        assert len(task.data) == 23

        form_data = {
            "AP": [
                {
                    "access": False,
                    "emails": False,
                    "cid": "kcm4zc",
                    "role": "Big Cheese"
                },
                {
                    "access": True,
                    "emails": True,
                    "cid": "lb3dp",
                    "role": "My Additional Role"
                }
            ]
        }

        self.complete_form(workflow, task, form_data)

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.name == 'Activity_Review_Before_Set_PB'
        assert len(task.data) == 24
        assert task.data['AP'] == form_data['AP']

        associated_users = self.get_associated_users(workflow_api.study_id)
        assert len(associated_users) == 1

        self.complete_form(workflow, task, {})

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.name == 'Activity_Review_Before_End'
        assert len(task.data) == 24

        associated_users = self.get_associated_users(workflow_api.study_id)
        assert len(associated_users) == 10
