from tests.base_test import BaseTest
from crc import app
from crc.models.ldap import LdapModel
from unittest.mock import patch
import os
import random
from unittest import skip


class TestSetPBAssociates(BaseTest):

    def create_additional_users(self):
        data = [('Alice Thompson', 'ghg3qe'), ('Brian Edwards', 'zxriuk'), ('Catherine Wilson', '80vn'),
             ('Daniel Martinez', '676pe'), ('Emily Johnson', 'tl5h'), ('Franklin Harris', 'y4suzz'),
             ('Georgia Clarke', 'jci60'), ('Henry Robinson', 'ouvhr'), ('Isabel Carter', 'dxigow'),
             ('Jack Peterson', 'w11ei'), ('Karen Bennett', 'jlzglh'), ('Louis Fisher', 'kump0'),
             ('Megan Richardson', 'xiai4c'), ('Nathan Cooper', '999hdr'), ('Olivia Scott', 'k8f6'),
             ('Patrick Howard', '51wqn0'), ('Quincy Parker', '934no'), ('Rachel Turner', 'd3cj0'),
             ('Samuel Baker', 'qmn3w8'), ('Teresa Mitchell', 'zcj7r'),]
        for (name, uid) in data:
            """LdapModel(uid=entry.uid.value,
                         display_name=entry.displayName.value,
                         given_name=", ".join(entry.givenName),
                         email_address=entry.mail.value,
                         telephone_number=entry.telephoneNumber.value,
                         title=", ".join(entry.title),
                         department=", ".join(entry.uvaDisplayDepartment),
                         affiliation=", ".join(entry.uvaPersonIAMAffiliation),
                         sponsor_type=", ".join(entry.uvaPersonSponsoredType))"""
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

    @skip
    @patch('crc.services.study_service.StudyService.get_investigators')  # mock_investigators
    def test_set_pb_associates(self, mock_investigators):
        app.config['PB_ENABLED'] = True
        self.add_users()  # adds users in test ldap
        self.create_additional_users()

        mock_investigators.return_value.ok = True
        mock_investigators.return_value = \
            {'PI': {'code': 'PI', 'label': 'Primary Investigator', 'display': 'Always', 'unique': 'Yes',
                    'user_id': 'cm4r', 'uid': 'cm4r', 'display_name': 'Carol A Manning', 'given_name': 'Carol',
                    'email_address': 'cm4r@virginia.edu', 'telephone_number': '4349821012',
                    'title': 'E1:Clinician Physician, E0:Professor',
                    'department': 'E1:UPG-MD-NEUR Neurology, E0:MD-NEUR Neurology', 'affiliation': 'faculty, staff',
                    'sponsor_type': '', 'date_cached': '2024-04-11T19:24:35.980782-04:00'},
             'SC_I': {'code': 'SC_I', 'label': 'Study Coordinator I', 'display': 'Always', 'unique': 'Yes',
                      'user_id': 'cdn4q', 'uid': 'cdn4q', 'display_name': 'Courtney Nightengale',
                      'given_name': 'Courtney', 'email_address': 'cdn4q@virginia.edu', 'telephone_number': '4342431927',
                      'title': 'E1:Temp D, E0:Compliance Analyst',
                      'department': 'E1:MD-OBGY Gyn Oncology, E0:MD-DMED Clinical Research Unit',
                      'affiliation': 'staff', 'sponsor_type': '', 'date_cached': '2024-04-23T14:50:11.759861-04:00'},
             'DEPT_CH': {'code': 'DEPT_CH', 'label': 'Department Chair', 'display': 'Always', 'unique': 'Yes',
                         'user_id': 'jpn2r', 'uid': 'jpn2r', 'display_name': 'James P Nataro', 'given_name': 'James',
                         'email_address': 'jpn2r@virginia.edu', 'telephone_number': '4349245093',
                         'title': 'E1:Clinician Physician, E0:Professor',
                         'department': 'E1:UPG-MD-PEDT Infectious Diseases, E0:MD-PEDT Pediatrics-Admin',
                         'affiliation': 'faculty, staff', 'sponsor_type': '',
                         'date_cached': '2024-04-11T19:26:17.849182-04:00'},
             'AS_C': {'code': 'AS_C', 'label': 'Additional Study Coordinators', 'display': 'Optional', 'unique': 'No',
                      'user_id': 'kcu5hm', 'uid': 'kcu5hm', 'display_name': 'Pat Junhasavasdikul', 'given_name': 'Pat',
                      'email_address': 'kcu5hm@virginia.edu', 'telephone_number': None, 'title': '',
                      'department': 'U1:Arts & Sciences Undergraduate', 'affiliation': 'student', 'sponsor_type': '',
                      'date_cached': '2025-01-08T08:50:23.340718-05:00'},
             'AS_C_2': {'code': 'AS_C', 'label': 'Additional Study Coordinators', 'display': 'Optional', 'unique': 'No',
                        'user_id': 'lmw2d', 'uid': 'lmw2d', 'display_name': 'Lindsey Sites', 'given_name': 'Lindsey',
                        'email_address': 'lmw2d@virginia.edu', 'telephone_number': '4349823500',
                        'title': 'E1:APP - CRNA Saturday Elective, E0:Lead RN Anesthetist',
                        'department': "E1:Anesthesia CRNA's, E0:Anesthesia CRNA's",
                        'affiliation': 'alumni, staff, former_student', 'sponsor_type': '',
                        'date_cached': '2025-01-08T09:06:07.004507-05:00'},
             'SI': {'code': 'SI', 'label': 'Sub Investigator', 'display': 'Optional', 'unique': 'No',
                    'user_id': 'ghg3qe', 'uid': 'ghg3qe', 'display_name': 'Jessica L Morris', 'given_name': 'Jessica',
                    'email_address': 'ghg3qe@virginia.edu', 'telephone_number': '4349821058',
                    'title': 'E0:Compliance Manager-CMPL74', 'department': 'E0:MD-DMED Clinical Research Unit',
                    'affiliation': 'staff', 'sponsor_type': '', 'date_cached': '2024-04-23T12:47:09.643532-04:00'},
             'SI_2': {'code': 'SI', 'label': 'Sub Investigator', 'display': 'Optional', 'unique': 'No',
                      'user_id': 'pdb7u', 'uid': 'pdb7u', 'display_name': 'Penny D Baker', 'given_name': 'Penny',
                      'email_address': 'pdb7u@virginia.edu', 'telephone_number': '4349245078',
                      'title': 'E0:Patient Care Technician', 'department': 'E0:Perianesthesia Main',
                      'affiliation': 'staff', 'sponsor_type': '', 'date_cached': '2025-01-08T09:25:37.002183-05:00'},
             'SI_3': {'code': 'SI', 'label': 'Sub Investigator', 'display': 'Optional', 'unique': 'No',
                      'user_id': 'zzzz', 'error': 'ApiError: Unable to locate a user with id zzzz in LDAP. '},
             'IRBC': {'code': 'IRBC', 'label': 'IRB Coordinator', 'display': 'Optional', 'unique': 'Yes',
                      'user_id': 'jp2pz', 'uid': 'jp2pz', 'display_name': 'Jeff Pitts', 'given_name': 'Jeff',
                      'email_address': 'jp2pz@virginia.edu', 'telephone_number': '4349248590',
                      'title': 'E0:Software Engineer 4', 'department': 'E0:MD-DMED Research & Clinical Trial Analytics',
                      'affiliation': 'staff', 'sponsor_type': '', 'date_cached': '2024-04-17T12:31:02.593919-04:00'}}

        workflow = self.create_workflow('set_pb_associates')

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.name == 'Activity_Review_Before_Load_IRB'
        assert task.data == {}

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
        assert len(task.data['subs']) == 2
        assert len(task.data['subx']) == 1

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

        self.complete_form(workflow, task, {})

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        print('here')
