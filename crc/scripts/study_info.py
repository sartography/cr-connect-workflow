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
        return """StudyInfo [TYPE], where TYPE is one of 'info', 'investigators','required_docs', or 'details'
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
        study_info = {}
        if "study" in task.data:
            study_info = task.data["study"]

        if cmd == 'info':
            study = session.query(StudyModel).filter_by(id=study_id).first()
            schema = StudyModelSchema()
            study_info["info"] = schema.dump(study)
        if cmd == 'investigators':
            study_info["investigators"] = self.pb.get_investigators(study_id)
        if cmd == 'required_docs':
            study_info["required_docs"] = self.pb.get_required_docs(study_id)
        if cmd == 'details':
            study_info["details"] = self.pb.get_study_details(study_id)
        task.data["study"] = study_info


    def get_required_docs(self, study_id):
        required_docs = self.pb.get_required_docs(study_id)
        return required_docs










