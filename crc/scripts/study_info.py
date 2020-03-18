from pandas import ExcelFile

from crc import session, ma
from crc.api.common import ApiError
from crc.models.study import StudyModel, StudyModelSchema
from crc.scripts.script import Script, ScriptValidationError
from crc.services.file_service import FileService
from crc.services.protocol_builder import ProtocolBuilderService


class StudyInfo(Script):
    """Just your basic class that can pull in data from a few api endpoints and do a basic task."""
    pb = ProtocolBuilderService()
    type_options = ['info', 'investigators', 'required_docs', 'details']
    IRB_PRO_CATEGORIES_FILE = "irb_pro_categories.xls"

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
            study_info["required_docs"] = self.get_required_docs(study_id)
        if cmd == 'details':
            study_info["details"] = self.pb.get_study_details(study_id)
        task.data["study"] = study_info

    def get_required_docs(self, study_id):
        """Takes data from the protocol builder, and merges it with data from the IRB Pro Categories spreadsheet to return
        pertinant details about the required documents."""
        pb_docs = self.pb.get_required_docs(study_id)
        data_frame = self.get_file_reference_dictionary()
        required_docs = []
        for doc in pb_docs:
            required_docs.append(RequiredDocument.form_pb_and_spread_sheet(doc, data_frame))
        return required_docs

    def get_file_reference_dictionary(self):
        """Loads up the xsl file that contains the IRB Pro Categories and converts it to a Panda's data frame for processing."""
        data_model = FileService.get_reference_file_data(StudyInfo.IRB_PRO_CATEGORIES_FILE)
        xls = ExcelFile(data_model.data)
        df = xls.parse(xls.sheet_names[0])
        return df

    # Verifies that information is available for this script task to function
    # correctly. Returns a list of validation errors.
    @staticmethod
    def validate():
        errors = []
        try:
            FileService.get_reference_file_data(StudyInfo.IRB_PRO_CATEGORIES_FILE)
        except ApiError as ae:
            errors.append(ScriptValidationError.from_api_error(ae))
        return errors

class RequiredDocument(object):
    def __init__(self, pb_id, pb_name, category1, category2, category3, who_uploads, required, total_uploaded):
        self.protocol_builder_id = pb_id
        self.protocol_builder_name = pb_name
        self.category1 = category1
        self.category2 = category2
        self.category3 = category3
        self.who_uploads = who_uploads
        self.required = required
        self.total_uploaded = total_uploaded

    @classmethod
    def form_pb_and_spread_sheet(cls, pb_data, sheet_data):
        """Generates a Required Document record from protobol builder record and a Panda's data sheet"""
        return cls(pb_id=pb_data['AUXDOCID'],
                   pb_name=pb_data['AUXDOC'],
                   category1="")


class RequiredDocumentSchema(ma.Schema):
    class Meta:
        model = RequiredDocument
        fields = ["pb_id", "pb_name", "category1", "category2", "category3",
                  "who_uploads", "required", "total_uploaded"]
