from ldap3.core.exceptions import LDAPSocketOpenError

from crc import session, app
from crc.api.common import ApiError
from crc.models.study import StudyModel, StudySchema
from crc.models.workflow import WorkflowStatus
from crc.scripts.script import Script, ScriptValidationError
from crc.services.file_service import FileService
from crc.services.ldap_service import LdapService
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor


class StudyInfo(Script):

    """Just your basic class that can pull in data from a few api endpoints and do a basic task."""
    pb = ProtocolBuilderService()
    type_options = ['info', 'investigators', 'details', 'approvals', 'documents', 'protocol']

    def get_description(self):
        return """StudyInfo [TYPE], where TYPE is one of 'info', 'investigators', or 'details', 'approvals',
            'documents' or 'protocol'.
            Adds details about the current study to the Task Data.  The type of information required should be 
            provided as an argument.  'info' returns the basic information such as the title.  'Investigators' provides
            detailed information about each investigator in th study.  'Details' provides a large number
            of details about the study, as gathered within the protocol builder, and 'documents', 
            lists all the documents that can be a part of the study, with documents from Protocol Builder 
            marked as required, and details about any files that were uploaded' . 
        """

    def do_task_validate_only(self, task, study_id, *args, **kwargs):
        """For validation only, pretend no results come back from pb"""
        self.check_args(args)
        # Assure the reference file exists (a bit hacky, but we want to raise this error early, and cleanly.)
        FileService.get_file_reference_dictionary()
        data = {
            "study":{
                "info": {
                    "id": 12,
                    "title": "test",
                    "primary_investigator_id":21,
                    "user_uid": "dif84",
                    "sponsor": "sponsor",
                    "ind_number": "1234",
                    "inactive": False
                },
                "investigators":
                    {
                        "INVESTIGATORTYPE": "PI",
                        "INVESTIGATORTYPEFULL": "Primary Investigator",
                        "NETBADGEID": "dhf8r"
                    },
                "details":
                    {
                        "IS_IND": 0,
                        "IS_IDE": 0,
                        "IS_MULTI_SITE": 0,
                        "IS_UVA_PI_MULTI": 0
                    },
                "approvals": {
                    "study_id": 12,
                    "workflow_id": 321,
                    "display_name": "IRB API Details",
                    "name": "irb_api_details",
                    "status": WorkflowStatus.not_started.value,
                    "workflow_spec_id": "irb_api_details",
                },
                'protocol': {
                    id: 0,
                }
            }
        }
        self.add_data_to_task(task=task, data=data["study"])
        self.add_data_to_task(task, {"documents": StudyService().get_documents_status(study_id)})

    def do_task(self, task, study_id, *args, **kwargs):
        self.check_args(args)

        cmd = args[0]
        study_info = {}
        if self.__class__.__name__ in task.data:
            study_info = task.data[self.__class__.__name__]

        if cmd == 'info':
            study = session.query(StudyModel).filter_by(id=study_id).first()
            schema = StudySchema()
            self.add_data_to_task(task, {cmd: schema.dump(study)})
        if cmd == 'investigators':
            pb_response = self.pb.get_investigators(study_id)
            self.add_data_to_task(task, {cmd: self.organize_investigators_by_type(pb_response)})
        if cmd == 'details':
            self.add_data_to_task(task, {cmd: self.pb.get_study_details(study_id)})
        if cmd == 'approvals':
            self.add_data_to_task(task, {cmd: StudyService().get_approvals(study_id)})
        if cmd == 'documents':
            self.add_data_to_task(task, {cmd: StudyService().get_documents_status(study_id)})
        if cmd == 'protocol':
            self.add_data_to_task(task, {cmd: StudyService().get_protocol(study_id)})


    def check_args(self, args):
        if len(args) != 1 or (args[0] not in StudyInfo.type_options):
            raise ApiError(code="missing_argument",
                           message="The StudyInfo script requires a single argument which must be "
                                   "one of %s" % ",".join(StudyInfo.type_options))


    def organize_investigators_by_type(self, pb_investigators):
        """Convert array of investigators from protocol builder into a dictionary keyed on the type"""
        output = {}
        for i in pb_investigators:
            dict = {"user_id": i["NETBADGEID"], "type_full": i["INVESTIGATORTYPEFULL"]}
            dict.update(self.get_ldap_dict_if_available(i["NETBADGEID"]))
            output[i["INVESTIGATORTYPE"]] = dict
        return output

    def get_ldap_dict_if_available(self, user_id):
        try:
            ldap_service = LdapService()
            return ldap_service.user_info(user_id).__dict__
        except ApiError:
            app.logger.info(str(ApiError))
            return {}
        except LDAPSocketOpenError:
            app.logger.info("Failed to connect to LDAP Server.")
            return {}
