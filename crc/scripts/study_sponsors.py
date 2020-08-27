import json

from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.protocol_builder import ProtocolBuilderService


class StudySponsors(Script):
    """Please see the detailed description that is provided below. """

    pb = ProtocolBuilderService()

    # This is used for test/workflow validation, as well as documentation.
    example_data = [
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
        ]

    def example_to_string(self, key):
        return json.dumps(self.example_data['StudyInfo'][key], indent=2, separators=(',', ': '))

    def get_description(self):
        return ""
#        return """
# Returns a list of sponsors related to a study in the following format:
# {{example}}
#z        """.format(example=json.dumps(self.example_data, index=2, separators=(',', ': ')))

    def check_args(self, args):
        if len(args) > 0:
            raise ApiError(code="invalid_argument",
                           message="The Sponsor script does not take any arguments.  "
                                   "It returns the list of sponsors for the current study only. ")

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        """For validation only, pretend no results come back from pb"""
        self.check_args(args)
        return self.example_data

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.check_args(args)
        retval = ProtocolBuilderService.get_sponsors(study_id)
        # Check on returning box, as in return Box(retval) - may not work with list.
        return retval




