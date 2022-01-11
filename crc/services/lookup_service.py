import logging
import re
from collections import OrderedDict
from zipfile import BadZipFile

import pandas as pd
import numpy
from pandas import ExcelFile
from pandas._libs.missing import NA
from sqlalchemy import desc
from sqlalchemy.sql.functions import GenericFunction

from crc import db
from crc.api.common import ApiError
from crc.models.api_models import Task
from crc.models.file import FileModel, FileDataModel, LookupFileModel, LookupDataModel
from crc.models.ldap import LdapSchema
from crc.models.workflow import WorkflowModel, WorkflowSpecDependencyFile
from crc.services.file_service import FileService
from crc.services.spec_file_service import SpecFileService
from crc.services.ldap_service import LdapService
from crc.services.workflow_processor import WorkflowProcessor


class TSRank(GenericFunction):
    package = 'full_text'
    name = 'ts_rank'


class LookupService(object):
    """Provides tools for doing lookups for auto-complete fields, and rapid access to any
    uploaded spreadsheets.
    This can currently take three forms:
    1) Lookup from spreadsheet data associated with a workflow specification.
       in which case we store the spreadsheet data in a lookup table with full
       text indexing enabled, and run searches against that table.
    2) Lookup from spreadsheet data associated with a specific file.  This allows us
       to get a lookup model for a specific file object, such as a reference file.
    2) Lookup from LDAP records.  In which case we call out to an external service
       to pull back detailed records and return them.

    I could imagine this growing to include other external services as tools to handle
    lookup fields.  I could also imagine using some sort of local cache so we don't
    unnecessarily pound on external services for repeat searches for the same records.
    """

    @staticmethod
    def get_lookup_model(spiff_task, field):
        workflow_id = spiff_task.workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY]
        workflow = db.session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        return LookupService.__get_lookup_model(workflow, spiff_task.task_spec.name, field.id)

    @staticmethod
    def get_lookup_model_for_file_data(file_id, file_name, value_column, label_column):
        file_data = SpecFileService.get_reference_file_data(file_name)
        lookup_model = db.session.query(LookupFileModel).filter(LookupFileModel.file_model_id == file_id).first()
        if not lookup_model:
            logging.warning("!!!! Making a very expensive call to update the lookup model.")
            lookup_model = LookupService.build_lookup_table(file_id, file_name, file_data.data, value_column, label_column)
        return lookup_model

    @staticmethod
    def __get_lookup_model(workflow, task_spec_id, field_id):
        lookup_model = db.session.query(LookupFileModel) \
            .filter(LookupFileModel.workflow_spec_id == workflow.workflow_spec_id) \
            .filter(LookupFileModel.field_id == field_id) \
            .filter(LookupFileModel.task_spec_id == task_spec_id) \
            .order_by(desc(LookupFileModel.id)).first()

        # one more quick query, to see if the lookup file is still related to this workflow.
        # if not, we need to rebuild the lookup table.
        is_current = False
        if lookup_model:
            if lookup_model.is_ldap:  # LDAP is always current
                is_current = True
            else:
                is_current = db.session.query(WorkflowSpecDependencyFile). \
                    filter(WorkflowSpecDependencyFile.file_data_id == lookup_model.file_data_model_id).\
                    filter(WorkflowSpecDependencyFile.workflow_id == workflow.id).count()

        if not is_current:
            # Very very very expensive, but we don't know need this till we do.
            logging.warning("!!!! Making a very expensive call to update the lookup models.")
            lookup_model = LookupService.create_lookup_model(workflow, task_spec_id, field_id)

        return lookup_model

    @staticmethod
    def lookup(workflow, task_spec_id, field_id, query, value=None, limit=10):
        # Returns a list of dictionaries
        lookup_model = LookupService.__get_lookup_model(workflow, task_spec_id, field_id)

        if lookup_model.is_ldap:
            return LookupService._run_ldap_query(query, value, limit)
        else:
            return LookupService._run_lookup_query(lookup_model, query, value, limit)


    @staticmethod
    def create_lookup_model(workflow_model, task_spec_id, field_id):
        """
        This is all really expensive, but should happen just once (per file change).

        Checks to see if the options are provided in a separate lookup table associated with the workflow, and if so,
        assures that data exists in the database, and return a model than can be used to locate that data.

        Returns:  an array of LookupData, suitable for returning to the API.
        """
        processor = WorkflowProcessor(workflow_model)  # VERY expensive, Ludicrous for lookup / type ahead
        spec, field = processor.find_spec_and_field(task_spec_id, field_id)

        # Clear out all existing lookup models for this workflow and field.
        existing_models = db.session.query(LookupFileModel) \
            .filter(LookupFileModel.workflow_spec_id == workflow_model.workflow_spec_id) \
            .filter(LookupFileModel.task_spec_id == task_spec_id) \
            .filter(LookupFileModel.field_id == field_id).all()
        for model in existing_models:  # Do it one at a time to cause the required cascade of deletes.
            db.session.delete(model)

        #  Use the contents of a file to populate enum field options
        if field.has_property(Task.FIELD_PROP_SPREADSHEET_NAME):
            if not (field.has_property(Task.FIELD_PROP_VALUE_COLUMN) or
                    field.has_property(Task.FIELD_PROP_LABEL_COLUMN)):
                raise ApiError.from_task_spec("invalid_enum",
                                         "For enumerations based on an xls file, you must include 3 properties: %s, "
                                         "%s, and %s" % (Task.FIELD_PROP_SPREADSHEET_NAME,
                                                         Task.FIELD_PROP_VALUE_COLUMN,
                                                         Task.FIELD_PROP_LABEL_COLUMN),
                                         task_spec=spec)

            # Get the file data from the File Service
            file_name = field.get_property(Task.FIELD_PROP_SPREADSHEET_NAME)
            value_column = field.get_property(Task.FIELD_PROP_VALUE_COLUMN)
            label_column = field.get_property(Task.FIELD_PROP_LABEL_COLUMN)
            latest_files = SpecFileService().get_spec_data_files(workflow_spec_id=workflow_model.workflow_spec_id,
                                                           workflow_id=workflow_model.id,
                                                           name=file_name)
            if len(latest_files) < 1:
                raise ApiError("invalid_enum", "Unable to locate the lookup data file '%s'" % file_name)
            else:
                data_dict = latest_files[0]

            file_id = data_dict['meta']['id']
            file_name = data_dict['meta']['name']
            file_data = data_dict['data']
            lookup_model = LookupService.build_lookup_table(file_id, file_name, file_data, value_column, label_column,
                                                            workflow_model.workflow_spec_id, task_spec_id, field_id)

        #  Use the results of an LDAP request to populate enum field options
        elif field.has_property(Task.FIELD_PROP_LDAP_LOOKUP):
            lookup_model = LookupFileModel(workflow_spec_id=workflow_model.workflow_spec_id,
                                           task_spec_id=task_spec_id,
                                           field_id=field_id,
                                           is_ldap=True)

        else:
            raise ApiError.from_task_spec("unknown_lookup_option",
                           "Lookup supports using spreadsheet or LDAP options, "
                           "and neither of those was provided.", spec)
        db.session.add(lookup_model)
        db.session.commit()
        return lookup_model

    @staticmethod
    def build_lookup_table(file_id, file_name, file_data, value_column, label_column,
                           workflow_spec_id=None, task_spec_id=None, field_id=None):
        """ In some cases the lookup table can be very large.  This method will add all values to the database
         in a way that can be searched and returned via an api call - rather than sending the full set of
          options along with the form.  It will only open the file and process the options if something has
          changed.  """
        # if workflow_spec_id is not None:
        #     file_data = data_dict['data']
        # else:
        #     file_data = data_dict.data
        try:
            xlsx = ExcelFile(file_data, engine='openpyxl')
        # Pandas--or at least openpyxl, cannot read old xls files.
        # The error comes back as zipfile.BadZipFile because xlsx files are zipped xml files
        except BadZipFile:
            raise ApiError(code='excel_error',
                           message=f"Error opening excel file {file_name}. You may have an older .xls spreadsheet. (file_model_id: {file_id} workflow_spec_id: {workflow_spec_id}, task_spec_id: {task_spec_id}, and field_id: {field_id})")
        df = xlsx.parse(xlsx.sheet_names[0])  # Currently we only look at the fist sheet.
        df = df.convert_dtypes()
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')] # Drop unnamed columns.
        df = pd.DataFrame(df).dropna(how='all')  # Drop null rows
        df = pd.DataFrame(df).replace({NA: ''})

        if value_column not in df:
            raise ApiError("invalid_enum",
                           "The file %s does not contain a column named % s" % (file_name,
                                                                                value_column))
        if label_column not in df:
            raise ApiError("invalid_enum",
                           "The file %s does not contain a column named % s" % (file_name,
                                                                                label_column))

        lookup_model = LookupFileModel(workflow_spec_id=workflow_spec_id,
                                       field_id=field_id,
                                       task_spec_id=task_spec_id,
                                       file_model_id=file_id,
                                       is_ldap=False)

        db.session.add(lookup_model)
        for index, row in df.iterrows():
            lookup_data = LookupDataModel(lookup_file_model=lookup_model,
                                          value=row[value_column],
                                          label=row[label_column],
                                          data=row.to_dict(OrderedDict))
            db.session.add(lookup_data)
        db.session.commit()
        return lookup_model

    @staticmethod
    def _run_lookup_query(lookup_file_model, query, value, limit):
        db_query = LookupDataModel.query.filter(LookupDataModel.lookup_file_model == lookup_file_model)
        if value is not None:  # Then just find the model with that value
            db_query = db_query.filter(LookupDataModel.value == str(value))
        else:
            # Build a full text query that takes all the terms provided and executes each term as a prefix query, and
            # OR's those queries together.  The order of the results is handled as a standard "Like" on the original
            # string which seems to work intuitively for most entries.
            query = re.sub('[^A-Za-z0-9 ]+', '', query)  # Strip out non ascii characters.
            query = re.sub(r'\s+', ' ', query)  # Convert multiple space like characters to just one space, as we split on spaces.
            print("Query: " + query)
            query = query.strip()
            if len(query) > 0:
                if ' ' in query:
                    terms = query.split(' ')
                    new_terms = []
                    for t in terms:
                        new_terms.append("%s:*" % t)
                    new_query = ' & '.join(new_terms)
                    new_query = "'%s' | %s" % (query, new_query)
                else:
                    new_query = "%s:*" % query

                db_query = db_query.filter(
                    LookupDataModel.__ts_vector__.match(new_query,  postgresql_regconfig='simple'))

                # Hackishly order by like, which does a good job of pulling more relevant matches to the top.
                db_query = db_query.order_by(desc(LookupDataModel.label.like("%" + query + "%")))

        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.info(db_query)
        result = db_query.limit(limit).all()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
        result_data = list(map(lambda lookup_item: lookup_item.data, result))
        return result_data

    @staticmethod
    def _run_ldap_query(query, value, limit):
        if value:
            return [LdapSchema().dump(LdapService.user_info(value))]
        else:
            users = LdapService.search_users(query, limit)
        return users
