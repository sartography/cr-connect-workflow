import json

from crc import session
from crc.api.common import ApiError
from crc.models.protocol_builder import ProtocolBuilderInvestigatorType
from crc.models.study import StudyModel, StudySchema
from crc.models.workflow import WorkflowStatus
from crc.scripts.script import Script
from crc.services.file_service import FileService
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.study_service import StudyService
from box import Box

class StudyInfo(Script):
    """Please see the detailed description that is provided below. """

    pb = ProtocolBuilderService()
    type_options = ['info', 'investigators', 'roles', 'details', 'approvals', 'documents', 'protocol']

    # This is used for test/workflow validation, as well as documentation.
    example_data = {
        "StudyInfo": {
            "info": {
                "id": 12,
                "title": "test",
                "primary_investigator_id": 21,
                "user_uid": "dif84",
                "sponsor": "sponsor",
                "ind_number": "1234",
                "inactive": False
            },
            "investigators": {
                'PI': {
                    'label': ProtocolBuilderInvestigatorType.PI.value,
                    'display': 'Always',
                    'unique': 'Yes',
                    'user_id': 'dhf8r',
                    'display_name': 'Dan Funk',
                    'given_name': 'Dan',
                    'email': 'dhf8r@virginia.edu',
                    'telephone_number': '+1 (434) 924-1723',
                    'title': "E42:He's a hoopy frood",
                    'department': 'E0:EN-Eng Study of Parallel Universes',
                    'affiliation': 'faculty',
                    'sponsor_type': 'Staff'},
                'SC_I': {
                    'label': 'Study Coordinator I',
                    'display': 'Always',
                    'unique': 'Yes',
                    'user_id': None},
                'DC': {
                    'label': 'Department Contact',
                    'display': 'Optional',
                    'unique': 'Yes',
                    'user_id': 'asd3v',
                    'error': 'Unable to locate a user with id asd3v in LDAP'}
            },
            "documents": {
                'AD_CoCApp': {'category1': 'Ancillary Document', 'category2': 'CoC Application', 'category3': '',
                               'Who Uploads?': 'CRC', 'id': '12',
                               'description': 'Certificate of Confidentiality Application', 'required': False,
                               'study_id': 1, 'code': 'AD_CoCApp', 'display_name': 'Ancillary Document / CoC Application',
                               'count': 0, 'files': []},
                'UVACompl_PRCAppr': {'category1': 'UVA Compliance', 'category2': 'PRC Approval', 'category3': '',
                                  'Who Uploads?': 'CRC', 'id': '6', 'description': "Cancer Center's PRC Approval Form",
                                  'required': True, 'study_id': 1, 'code': 'UVACompl_PRCAppr',
                                  'display_name': 'UVA Compliance / PRC Approval', 'count': 1, 'files': [
                                     {'file_id': 10,
                                      'task_id': 'fakingthisout',
                                      'workflow_id': 2,
                                      'workflow_spec_id': 'docx'}],
                                      'status': 'complete'}
            },
            "details":
                {},
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

    def example_to_string(self, key):
        return json.dumps(self.example_data['StudyInfo'][key], indent=2, separators=(',', ': '))

    def get_description(self):
        return """
StudyInfo [TYPE], where TYPE is one of 'info', 'investigators', 'details', 'approvals',
'documents' or 'protocol'.

Adds details about the current study to the Task Data.  The type of information required should be 
provided as an argument.  The following arguments are available:

### Info ###
Returns the basic information such as the id and title
```
{info_example}
```

### Investigators ###
Returns detailed information about related personnel.
The order returned is guaranteed to match the order provided in the investigators.xslx reference file.
Detailed information is added in from LDAP about each personnel based on their user_id. 
```
{investigators_example}
```

### Investigator Roles ###
Returns a list of all investigator roles, populating any roles with additional information available from
the Protocol Builder and LDAP.  Its basically just like Investigators, but it includes all the roles, rather
that just those that were set in Protocol Builder.
```
{investigators_example}
```


### Details ###
Returns detailed information about variable keys read in from the Protocol Builder.

### Approvals ###
Returns data about the status of approvals related to a study.
```
{approvals_example}
```

### Documents ###
Returns a list of all documents that might be related to a study, reading all columns from the irb_documents.xsl 
file. Including information about any files that were uploaded or generated that relate to a given document. 
Please note this is just a few examples, ALL known document types are returned in an actual call.
```
{documents_example}
```

### Protocol ###
Returns information specific to the protocol. 


        """.format(info_example=self.example_to_string("info"),
                   investigators_example=self.example_to_string("investigators"),
                   approvals_example=self.example_to_string("approvals"),
                   documents_example=self.example_to_string("documents"),
                   )

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        """For validation only, pretend no results come back from pb"""
        self.check_args(args,2)
        # Assure the reference file exists (a bit hacky, but we want to raise this error early, and cleanly.)
        FileService.get_reference_file_data(FileService.DOCUMENT_LIST)
        FileService.get_reference_file_data(FileService.INVESTIGATOR_LIST)
        data = Box({
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
                "investigators": {
                    "PI": {
                        "label": ProtocolBuilderInvestigatorType.PI.value,
                        "display": "Always",
                        "unique": "Yes",
                        "user_id": "dhf8r",
                        "title": "",
                        "display_name": "Daniel Harold Funk",
                        "sponsor_type": "Contractor",
                        "telephone_number": "0000000000",
                        "department": "",
                        "email_address": "dhf8r@virginia.edu",
                        "given_name": "Daniel",
                        "uid": "dhf8r",
                        "affiliation": "",
                        "date_cached": "2020-08-04T19:32:08.006128+00:00"
                    },
                    "SC_I": {
                        "label": ProtocolBuilderInvestigatorType.SC_I.value,
                        "display": "Always",
                        "unique": "Yes",
                        "user_id": "ajl2j",
                        "title": "",
                        "display_name": "Aaron Louie",
                        "sponsor_type": "Contractor",
                        "telephone_number": "0000000000",
                        "department": "",
                        "email_address": "ajl2j@virginia.edu",
                        "given_name": "Aaron",
                        "uid": "ajl2j",
                        "affiliation": "sponsored",
                        "date_cached": "2020-08-04T19:32:10.699666+00:00"
                    },
                    "SC_II": {
                        "label": ProtocolBuilderInvestigatorType.SC_II.value,
                        "display": "Optional",
                        "unique": "Yes",
                        "user_id": "cah3us",
                        "title": "",
                        "display_name": "Alex Herron",
                        "sponsor_type": "Contractor",
                        "telephone_number": "0000000000",
                        "department": "",
                        "email_address": "cah3us@virginia.edu",
                        "given_name": "Alex",
                        "uid": "cah3us",
                        "affiliation": "sponsored",
                        "date_cached": "2020-08-04T19:32:10.075852+00:00"
                    },
                },
                "pi": {
                    "PI": {
                        "label": ProtocolBuilderInvestigatorType.PI.value,
                        "display": "Always",
                        "unique": "Yes",
                        "user_id": "dhf8r",
                        "title": "",
                        "display_name": "Daniel Harold Funk",
                        "sponsor_type": "Contractor",
                        "telephone_number": "0000000000",
                        "department": "",
                        "email_address": "dhf8r@virginia.edu",
                        "given_name": "Daniel",
                        "uid": "dhf8r",
                        "affiliation": "",
                        "date_cached": "2020-08-04T19:32:08.006128+00:00"
                    }
                },
                "roles":
                    {
                        "INVESTIGATORTYPE": "PI",
                        "INVESTIGATORTYPEFULL": ProtocolBuilderInvestigatorType.PI.value,
                        "NETBADGEID": "dhf8r"
                    },
                "details":
                    {
                        "DSMB": None,
                        "DSMB_FREQUENCY": None,
                        "GCRC_NUMBER": None,
                        "IBC_NUMBER": None,
                        "IDE": None,
                        "IND_1": 1234,
                        "IND_2": None,
                        "IND_3": None,
                        "IRBREVIEWERADMIN": None,
                        "IS_ADULT_PARTICIPANT": None,
                        "IS_APPROVED_DEVICE": None,
                        "IS_AUX": None,
                        "IS_BIOMEDICAL": None,
                        "IS_CANCER_PATIENT": None,
                        "IS_CENTRAL_REG_DB": None,
                        "IS_CHART_REVIEW": None,
                        "IS_COMMITTEE_CONFLICT": None,
                        "IS_CONSENT_WAIVER": None,
                        "IS_DB": None,
                        "IS_ELDERLY_POP": None,
                        "IS_ENGAGED_RESEARCH": None,
                        "IS_FETUS_POP": None,
                        "IS_FINANCIAL_CONFLICT": None,
                        "IS_FOR_CANCER_CENTER": None,
                        "IS_FUNDING_SOURCE": None,
                        "IS_GCRC": None,
                        "IS_GENE_TRANSFER": None,
                        "IS_GRANT": None,
                        "IS_HGT": None,
                        "IS_IBC": None,
                        "IS_IDE": None,
                        "IS_IND": None,
                        "IS_MENTAL_IMPAIRMENT_POP": None,
                        "IS_MINOR": None,
                        "IS_MINOR_PARTICIPANT": None,
                        "IS_MULTI_SITE": None,
                        "IS_NOT_CONSENT_WAIVER": None,
                        "IS_NOT_PRC_WAIVER": None,
                        "IS_OTHER_VULNERABLE_POP": None,
                        "IS_OUTSIDE_CONTRACT": None,
                        "IS_PI_INITIATED": None,
                        "IS_PI_SCHOOL": None,
                        "IS_PRC": None,
                        "IS_PRC_DSMP": None,
                        "IS_PREGNANT_POP": None,
                        "IS_PRISONERS_POP": None,
                        "IS_QUALITATIVE": None,
                        "IS_RADIATION": None,
                        "IS_REVIEW_BY_CENTRAL_IRB": None,
                        "IS_SPONSOR": None,
                        "IS_SPONSOR_MONITORING": None,
                        "IS_SURROGATE_CONSENT": None,
                        "IS_TISSUE_BANKING": None,
                        "IS_UVA_DB": None,
                        "IS_UVA_IDE": None,
                        "IS_UVA_IND": None,
                        "IS_UVA_LOCATION": None,
                        "IS_UVA_PI_MULTI": None,
                        "MULTI_SITE_LOCATIONS": None,
                        "NON_UVA_LOCATION": None,
                        "OTHER_VULNERABLE_DESC": None,
                        "PRC_NUMBER": None,
                        "SPONSORS_PROTOCOL_REVISION_DATE": None,
                        "UPLOAD_COMPLETE": None
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
                    'id': 0,
                }
            }
        })
        if args[0]=='documents':
            return StudyService().get_documents_status(study_id)
        return data['study'][args[0]]
        #self.add_data_to_task(task=task, data=data["study"])
        #self.add_data_to_task(task, {"documents": StudyService().get_documents_status(study_id)})

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.check_args(args,2)
        prefix = None
        if len(args) > 1:
            prefix = args[1]
        cmd = args[0]
        # study_info = {}
        # if self.__class__.__name__ in task.data:
        #     study_info = task.data[self.__class__.__name__]
        retval = None
        if cmd == 'info':
            study = session.query(StudyModel).filter_by(id=study_id).first()
            schema = StudySchema()
            retval = schema.dump(study)
        if cmd == 'investigators':
            retval = StudyService().get_investigators(study_id)
        if cmd == 'roles':
            retval = StudyService().get_investigators(study_id, all=True)
        if cmd == 'details':
            retval = self.pb.get_study_details(study_id)
        if cmd == 'approvals':
            retval = StudyService().get_approvals(study_id)
        if cmd == 'documents':
            retval = StudyService().get_documents_status(study_id)
        if cmd == 'protocol':
            retval = StudyService().get_protocol(study_id)
        if isinstance(retval,dict) and prefix is not None:
            return Box({x:retval[x] for x in retval.keys() if x[:len(prefix)] == prefix})
        elif isinstance(retval,dict):
            return Box(retval)
        else:
            return retval



    def check_args(self, args, maxlen=1):
        if len(args) < 1 or len(args) > maxlen or (args[0] not in StudyInfo.type_options):
            raise ApiError(code="missing_argument",
                           message="The StudyInfo script requires a single argument which must be "
                                   "one of %s" % ",".join(StudyInfo.type_options))


