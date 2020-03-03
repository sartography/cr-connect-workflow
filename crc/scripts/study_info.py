import requests

from crc import session
from crc.api.common import ApiError
from crc.models.study import StudyModel, StudyModelSchema
from crc.scripts.script import Script
from crc.services.protocol_builder import ProtocolBuilderService


class StudyInfo(Script):
    """Just your basic class that can pull in data from a few api endpoints and do a basic task."""
    pb = ProtocolBuilderService()
    type_options = ['info', 'investigators', 'required_docs', 'details']

    def get_description(self):
        return """
            StudyInfo [TYPE] is one of 'info', 'investigators','required_docs', 'details'
            Adds details about the current study to the Task Data.  The type of information required should be 
            provided as an argument.  Basic returns the basic information such as the title.  Investigators provides
            detailed information about each investigator in th study.  Details provides a large number
            of details about the study, as gathered within the protocol builder, and 'required_docs', 
            lists all the documents the Protocol Builder has determined will be required as a part of
            this study. 
        """

    def do_task(self, task, study_id, *args, **kwargs):
        if len(args) != 1 or (args[0] not in StudyInfo.type_options):
            raise ApiError(code="missing_argument",
                           message="The StudyInfo script requires a single argument which must be "
                                   "one of %s" % ",".join(StudyInfo.type_options))
        cmd = args[0]
        if cmd == 'info':
            study = session.query(StudyModel).filter_by(id=study_id).first()
            schema = StudyModelSchema()
            details = {"study": {"info": schema.dump(study)}}
            task.data.update(details)
        if cmd == 'investigators':
            details = {"study": {"investigators": self.pb.get_investigators(study_id)}}
            task.data.update(details)
        if cmd == 'required_docs':
            details = {"study": {"required_docs": self.pb.get_required_docs(study_id)}}
            task.data.update(details)
        if cmd == 'details':
            details = {"study": {"details": self.pb.get_study_details(study_id)}}
            task.data.update(details)

