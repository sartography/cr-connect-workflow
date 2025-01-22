from tests.base_test import BaseTest

from crc.services.file_system_service import FileSystemService
from crc import app
from unittest.mock import patch
import os

from crc.services.protocol_builder import ProtocolBuilderService


class TestLoadIRBPersonnel(BaseTest):
    test_study_id = 1
    test_uid = "dhf8r"
    spec_path = FileSystemService.root_path()
    import_spec_path = os.path.join(app.root_path, '..', 'tests', 'data', 'load_irb_personnel', 'DATA')

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    @patch('crc.services.study_service.StudyService.get_investigators')  # mock_investigators
    def test_load_basic_personnel(self, mock_investigators, mock_studies):
        """This tests the load_irb_personnel script.
        We mock a known set of associated users, and test the output of the script.

        This tests a good assortment of associated users."""

        self.create_reference_document()

        app.config['PB_ENABLED'] = True
        mock_investigators.return_value.ok = True
        mock_investigators.return_value = \
            {'PI': {'code': 'PI', 'label': 'Primary Investigator', 'display': 'Always', 'unique': 'Yes',
                    'user_id': 'acl53c', 'uid': 'acl53c', 'display_name': 'Dr. Evelyn Carter',
                    'email_address': 'acl53c@virginia.edu', 'title': 'E1:Clinician Physician, E0:Professor',
                    'department': 'E1:UPG-MD-NEUR Neurology, E0:MD-NEUR Neurology', 'affiliation': 'faculty, staff',
                    'sponsor_type': '','telephone_number': '1925168475', 'date_cached': '2021-09-29T14:00:00Z'},
             'SC_I': {'code': 'SC_I', 'label': 'Study Coordinator I', 'display': 'Always', 'unique': 'Yes',
                      'user_id': '7tnd', 'uid': '7tnd', 'display_name': 'James Whitaker',
                      'email_address': '7tnd@virginia.edu', 'title': 'E1:Temp D, E0:Compliance Analyst',
                      'department': 'E1:MD-OBGY Gyn Oncology, E0:MD-DMED Clinical Research Unit',
                      'affiliation': 'staff', 'sponsor_type': '', 'telephone_number': '6434937557',
                      'date_cached': '2021-09-29T14:00:00Z'},
             'DEPT_CH': {'code': 'DEPT_CH', 'label': 'Department Chair', 'display': 'Always', 'unique': 'Yes',
                         'user_id': 'nd9i4', 'uid': 'nd9i4', 'display_name': 'Sophia Ramirez',
                         'email_address': 'nd9i4@virginia.edu', 'title': 'E1:Clinician Physician, E0:Professor',
                         'department': 'E1:UPG-MD-PEDT Infectious Diseases, E0:MD-PEDT Pediatrics-Admin',
                         'affiliation': 'faculty, staff', 'sponsor_type': '','telephone_number': '7136895308',
                         'date_cached': '2021-09-29T14:00:00Z'},
             'AS_C': {'code': 'AS_C', 'label': 'Additional Study Coordinators', 'display': 'Optional', 'unique': 'No',
                      'user_id': 'fwdnjd', 'uid': 'fwdnjd', 'display_name': 'David Chen',
                      'email_address': 'fwdnjd@virginia.edu', 'title': '',
                      'department': 'U1:Arts & Sciences Undergraduate', 'affiliation': 'student', 'sponsor_type': '',
                      'telephone_number': '5289542712', 'date_cached': '2021-09-29T14:00:00Z'},
             'AS_C_2': {'code': 'AS_C', 'label': 'Additional Study Coordinators', 'display': 'Optional', 'unique': 'No',
                        'user_id': 'vi8db7', 'uid': 'vi8db7', 'display_name': 'Lindsey Sites',
                        'email_address': 'vi8db7@virginia.edu',
                        'title': 'E1:APP - CRNA Saturday Elective, E0:Lead RN Anesthetist',
                        'department': "E1:Anesthesia CRNA's, E0:Anesthesia CRNA's",
                        'affiliation': 'alumni, staff, former_student', 'sponsor_type': '',
                        'telephone_number': '2842240435', 'date_cached': '2021-09-29T14:00:00Z'},
             'SI': {'code': 'SI', 'label': 'Sub Investigator', 'display': 'Optional', 'unique': 'No',
                    'user_id': 'f90si', 'uid': 'f90si', 'display_name': 'Michael Bennett',
                    'email_address': 'f90si@virginia.edu', 'title': 'E0:Compliance Manager-CMPL74',
                    'department': 'E0:MD-DMED Clinical Research Unit', 'affiliation': 'staff', 'sponsor_type': '',
                    'telephone_number': '7183446492', 'date_cached': '2021-09-29T14:00:00Z'},
             'SI_2': {'code': 'SI', 'label': 'Sub Investigator', 'display': 'Optional', 'unique': 'No',
                      'user_id': '0i2qgy', 'uid': '0i2qgy', 'display_name': 'Anna Fletcher',
                      'email_address': '0i2qgy@virginia.edu', 'title': 'E0:Patient Care Technician',
                      'department': 'E0:Perianesthesia Main', 'affiliation': 'staff', 'sponsor_type': '',
                      'telephone_number': '3205771078', 'date_cached': '2021-09-29T14:00:00Z'},
             'SI_3': {'code': 'SI', 'label': 'Sub Investigator', 'display': 'Optional', 'unique': 'No',
                      'user_id': 'zzzz', 'error': 'ApiError: Unable to locate a user with id zzzz in LDAP. '},
             'IRBC': {'code': 'IRBC', 'label': 'IRB Coordinator', 'display': 'Optional', 'unique': 'Yes',
                      'user_id': 'ewy7iq', 'uid': 'ewy7iq', 'display_name': 'Isabella Nguyen',
                      'email_address': 'ewy7iq@virginia.edu', 'title': 'E0:Software Engineer 4',
                      'department': 'E0:MD-DMED Research & Clinical Trial Analytics', 'affiliation': 'staff',
                      'sponsor_type': '','telephone_number': '8040739988', 'date_cached': '2021-09-29T14:00:00Z'}
             }

        mock_studies.return_value.ok = True
        mock_studies.return_value.text = self.protocol_builder_response('user_studies.json')

        workflow = self.create_workflow('load_irb_personnel')
        # investigator_response = ProtocolBuilderService.get_investigators(self.test_study_id)
        # study_response = ProtocolBuilderService.get_studies(self.test_uid)

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        data = task.data

        assert 'irb_personnel_data' in data
        irb_personnel_data = data['irb_personnel_data']

        for key in ['pi', 'dc', 'pcs', 'pcpb', 'subs', 'subpb', 'subx', 'is_pbc_pi', 'is_pbc_dc', 'is_pbc_pc',
                    'is_pbc_subs', 'cnt_pcs', 'cnt_pcpb', 'cnt_subs', 'cnt_subpb', 'hasPI', 'hasDC', 'pi_invalid_uid',
                    'dc_invalid_uid', 'pcs_invalid_uid', 'subs_invalid_uid']:
            assert key in irb_personnel_data

        assert irb_personnel_data['pi'] == {'code': 'PI', 'label': 'Primary Investigator', 'user_id': 'acl53c', 'uid': 'acl53c', 'display_name': 'Dr. Evelyn Carter', 'email_address': 'acl53c@virginia.edu', 'title': 'E1:Clinician Physician, E0:Professor', 'department': 'E1:UPG-MD-NEUR Neurology, E0:MD-NEUR Neurology', 'affiliation': 'faculty, staff', 'sponsor_type': '', 'E0': {}}
        assert irb_personnel_data['dc'] == {'code': 'DEPT_CH', 'label': 'Department Chair', 'user_id': 'nd9i4', 'uid': 'nd9i4', 'display_name': 'Sophia Ramirez', 'email_address': 'nd9i4@virginia.edu', 'title': 'E1:Clinician Physician, E0:Professor', 'department': 'E1:UPG-MD-PEDT Infectious Diseases, E0:MD-PEDT Pediatrics-Admin', 'affiliation': 'faculty, staff', 'sponsor_type': '', 'E0': {}}
        assert irb_personnel_data['pcs'] == {'SC_I': {'code': 'SC_I', 'label': 'Study Coordinator I', 'user_id': '7tnd', 'uid': '7tnd', 'display_name': 'James Whitaker', 'email_address': '7tnd@virginia.edu', 'title': 'E1:Temp D, E0:Compliance Analyst', 'department': 'E1:MD-OBGY Gyn Oncology, E0:MD-DMED Clinical Research Unit', 'affiliation': 'staff', 'sponsor_type': ''}, 'AS_C': {'code': 'AS_C', 'label': 'Additional Study Coordinators', 'user_id': 'fwdnjd', 'uid': 'fwdnjd', 'display_name': 'David Chen', 'email_address': 'fwdnjd@virginia.edu', 'title': '', 'department': 'U1:Arts & Sciences Undergraduate', 'affiliation': 'student', 'sponsor_type': ''}, 'AS_C_2': {'code': 'AS_C', 'label': 'Additional Study Coordinators', 'user_id': 'vi8db7', 'uid': 'vi8db7', 'display_name': 'Lindsey Sites', 'email_address': 'vi8db7@virginia.edu', 'title': 'E1:APP - CRNA Saturday Elective, E0:Lead RN Anesthetist', 'department': "E1:Anesthesia CRNA's, E0:Anesthesia CRNA's", 'affiliation': 'alumni, staff, former_student', 'sponsor_type': ''}, 'IRBC': {'code': 'IRBC', 'label': 'IRB Coordinator', 'user_id': 'ewy7iq', 'uid': 'ewy7iq', 'display_name': 'Isabella Nguyen', 'email_address': 'ewy7iq@virginia.edu', 'title': 'E0:Software Engineer 4', 'department': 'E0:MD-DMED Research & Clinical Trial Analytics', 'affiliation': 'staff', 'sponsor_type': ''}}
        assert irb_personnel_data['pcpb'] == {}
        assert irb_personnel_data['subs'] == {'SI': {'code': 'SI', 'label': 'Sub Investigator', 'user_id': 'f90si', 'uid': 'f90si', 'display_name': 'Michael Bennett', 'email_address': 'f90si@virginia.edu', 'title': 'E0:Compliance Manager-CMPL74', 'department': 'E0:MD-DMED Clinical Research Unit', 'affiliation': 'staff', 'sponsor_type': ''}, 'SI_2': {'code': 'SI', 'label': 'Sub Investigator', 'user_id': '0i2qgy', 'uid': '0i2qgy', 'display_name': 'Anna Fletcher', 'email_address': '0i2qgy@virginia.edu', 'title': 'E0:Patient Care Technician', 'department': 'E0:Perianesthesia Main', 'affiliation': 'staff', 'sponsor_type': ''}}
        assert irb_personnel_data['subpb'] == {}
        assert irb_personnel_data['subx'] == {'SI_3': {'code': 'SI', 'display': 'Optional', 'error': 'ApiError: Unable to locate a user with id zzzz in LDAP. ', 'label': 'Sub Investigator', 'unique': 'No', 'user_id': 'zzzz'}}

        assert irb_personnel_data['is_pbc_pi'] is False
        assert irb_personnel_data['is_pbc_dc'] is False
        assert irb_personnel_data['is_pbc_pc'] is False
        assert irb_personnel_data['is_pbc_subs'] is False
        assert irb_personnel_data['cnt_pcs'] == 4
        assert irb_personnel_data['cnt_pcpb'] == 0
        assert irb_personnel_data['cnt_subs'] == 2
        assert irb_personnel_data['cnt_subpb'] == 0
        assert irb_personnel_data['hasPI'] is True
        assert irb_personnel_data['hasDC'] is True
        assert irb_personnel_data['pi_invalid_uid'] is False
        assert irb_personnel_data['dc_invalid_uid'] is False
        assert irb_personnel_data['pcs_invalid_uid'] is False
        assert irb_personnel_data['subs_invalid_uid'] is True
