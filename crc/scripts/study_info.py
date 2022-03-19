import json

from SpiffWorkflow.bpmn.PythonScriptEngine import Box
from SpiffWorkflow.util.metrics import timeit

from crc import session
from crc.api.common import ApiError
from crc.models.protocol_builder import ProtocolBuilderInvestigatorType
from crc.models.study import StudyModel, StudySchema
from crc.scripts.script import Script
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.study_service import StudyService


class StudyInfo(Script):
    """Please see the detailed description that is provided below. """

    pb = ProtocolBuilderService()
    type_options = ['info', 'investigators', 'roles', 'details', 'documents', 'sponsors']

    # This is used for test/workflow validation, as well as documentation.
    example_data = {
        "StudyInfo": {
            "info": {
                "id": 12,
                "title": "test",
                "user_uid": "dif84",
                "sponsor": "sponsor",
                "ind_number": "1234",
                "inactive": False
            },
            "sponsors": [
                {
                    "COMMONRULEAGENCY": None,
                    "SPONSOR_ID": 2453,
                    "SP_NAME": "Abbott Ltd",
                    "SP_TYPE": "Private",
                    "SP_TYPE_GROUP_NAME": None,
                    "SS_STUDY": 2
                },
                {
                    "COMMONRULEAGENCY": None,
                    "SPONSOR_ID": 2387,
                    "SP_NAME": "Abbott-Price",
                    "SP_TYPE": "Incoming Sub Award",
                    "SP_TYPE_GROUP_NAME": "Government",
                    "SS_STUDY": 2
                },
                {
                    "COMMONRULEAGENCY": None,
                    "SPONSOR_ID": 1996,
                    "SP_NAME": "Abernathy-Heidenreich",
                    "SP_TYPE": "Foundation/Not for Profit",
                    "SP_TYPE_GROUP_NAME": "Other External Funding",
                    "SS_STUDY": 2
                }
            ],

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
                    'error': 'Unable to locate a user with id asd3v in LDAP'},
                'DEPT_CH': {
                    'label': 'Department Chair',
                    'display': 'Always',
                    'unique': 'Yes',
                    'user_id': 'lb3dp'}
            },
            "documents": {
                'AD_CoCApp': {'category1': 'Ancillary Document', 'category2': 'CoC Application', 'category3': '',
                              'Who Uploads?': 'CRC', 'id': '12',
                              'description': 'Certificate of Confidentiality Application', 'required': False,
                              'study_id': 1, 'code': 'AD_CoCApp',
                              'display_name': 'Ancillary Document / CoC Application',
                              'count': 0, 'files': []},
                'UVACompl_PRCAppr': {'category1': 'UVA Compliance', 'category2': 'PRC Approval', 'category3': '',
                                     'Who Uploads?': 'CRC', 'id': '6',
                                     'description': "Cancer Center's PRC Approval Form",
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
        }
    }

    def example_to_string(self, key):
        return json.dumps(self.example_data['StudyInfo'][key], indent=2, separators=(',', ': '))

    def get_description(self):
        return """study_info(TYPE), where TYPE is one of 'info', 'investigators', 'details', or 'documents'.

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

### Documents ###
Returns a list of all documents that might be related to a study, reading all columns from the irb_documents.xsl 
file. Including information about any files that were uploaded or generated that relate to a given document. 
Please note this is just a few examples, ALL known document types are returned in an actual call.
```
{documents_example}
```


        """.format(info_example=self.example_to_string("info"),
                   investigators_example=self.example_to_string("investigators"),
                   documents_example=self.example_to_string("documents"),
                   )

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        # we call the real do_task so we can
        # seed workflow validations with settings from studies in PB Mock
        # in order to test multiple paths thru the workflow
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.check_args(args, 2)
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
            details = self.pb.get_study_details(study_id)
            if len(details) > 0:
                retval = details[0]
            else:
                retval = None
        if cmd == 'sponsors':
            retval = self.pb.get_sponsors(study_id)
        if cmd == 'documents':
            retval = StudyService().get_documents_status(study_id)

        return self.box_it(retval, prefix)

    def box_it(self, retval, prefix = None):
        if isinstance(retval, list):
            return [Box(item) for item in retval]
        if isinstance(retval, dict) and prefix is not None:
            return Box({x: retval[x] for x in retval.keys() if x[:len(prefix)] == prefix})
        elif isinstance(retval, dict):
            return Box(retval)


    def check_args(self, args, maxlen=1):
        if len(args) < 1 or len(args) > maxlen or (args[0] not in StudyInfo.type_options):
            raise ApiError(code="missing_argument",
                           message="The StudyInfo script requires a single argument which must be "
                                   "one of %s" % ",".join(StudyInfo.type_options))
