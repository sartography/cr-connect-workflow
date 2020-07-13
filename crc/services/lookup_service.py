import logging
import re
from collections import OrderedDict

import pandas as pd
from pandas import ExcelFile, np
from sqlalchemy import func, desc
from sqlalchemy.sql.functions import GenericFunction

from crc import db
from crc.api.common import ApiError
from crc.models.api_models import Task
from crc.models.file import FileDataModel, LookupFileModel, LookupDataModel
from crc.models.workflow import WorkflowModel, WorkflowSpecDependencyFile
from crc.services.file_service import FileService
from crc.services.ldap_service import LdapService
from crc.services.workflow_processor import WorkflowProcessor


class TSRank(GenericFunction):
    package = 'full_text'
    name = 'ts_rank'


class LookupService(object):
    """Provides tools for doing lookups for auto-complete fields.
    This can currently take two forms:
    1) Lookup from spreadsheet data associated with a workflow specification.
       in which case we store the spreadsheet data in a lookup table with full
       text indexing enabled, and run searches against that table.
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
        return LookupService.__get_lookup_model(workflow, field.id)

    @staticmethod
    def __get_lookup_model(workflow, field_id):
        lookup_model = db.session.query(LookupFileModel) \
            .filter(LookupFileModel.workflow_spec_id == workflow.workflow_spec_id) \
            .filter(LookupFileModel.field_id == field_id) \
            .order_by(desc(LookupFileModel.id)).first()

        # one more quick query, to see if the lookup file is still related to this workflow.
        # if not, we need to rebuild the lookup table.
        is_current = False
        if lookup_model:
            is_current = db.session.query(WorkflowSpecDependencyFile). \
                filter(WorkflowSpecDependencyFile.file_data_id == lookup_model.file_data_model_id).\
                filter(WorkflowSpecDependencyFile.workflow_id == workflow.id).count()

        if not is_current:
            # Very very very expensive, but we don't know need this till we do.
            lookup_model = LookupService.create_lookup_model(workflow, field_id)

        return lookup_model

    @staticmethod
    def lookup(workflow, field_id, query, value=None, limit=10):

        lookup_model = LookupService.__get_lookup_model(workflow, field_id)

        if lookup_model.is_ldap:
            return LookupService._run_ldap_query(query, limit)
        else:
            return LookupService._run_lookup_query(lookup_model, query, value, limit)

    @staticmethod
    def create_lookup_model(workflow_model, field_id):
        """
         This is all really expensive, but should happen just once (per file change).
         Checks to see if the options are provided in a separate lookup table associated with the
        workflow, and if so, assures that data exists in the database, and return a model than can be used
        to locate that data.
        Returns:  an array of LookupData, suitable for returning to the api.
        """
        processor = WorkflowProcessor(workflow_model)  # VERY expensive, Ludicrous for lookup / type ahead
        spiff_task, field = processor.find_task_and_field_by_field_id(field_id)

        # Clear out all existing lookup models for this workflow and field.
        existing_models = db.session.query(LookupFileModel) \
            .filter(LookupFileModel.workflow_spec_id == workflow_model.workflow_spec_id) \
            .filter(LookupFileModel.field_id == field_id).all()
        for model in existing_models:  # Do it one at a time to cause the required cascade of deletes.
            db.session.delete(model)


        if field.has_property(Task.PROP_OPTIONS_FILE):
            if not field.has_property(Task.PROP_OPTIONS_VALUE_COLUMN) or \
                    not field.has_property(Task.PROP_OPTIONS_LABEL_COL):
                raise ApiError.from_task("invalid_emum",
                                         "For enumerations based on an xls file, you must include 3 properties: %s, "
                                         "%s, and %s" % (Task.PROP_OPTIONS_FILE,
                                                         Task.PROP_OPTIONS_VALUE_COLUMN,
                                                         Task.PROP_OPTIONS_LABEL_COL),
                                         task=spiff_task)

            # Get the file data from the File Service
            file_name = field.get_property(Task.PROP_OPTIONS_FILE)
            value_column = field.get_property(Task.PROP_OPTIONS_VALUE_COLUMN)
            label_column = field.get_property(Task.PROP_OPTIONS_LABEL_COL)
            latest_files = FileService.get_spec_data_files(workflow_spec_id=workflow_model.workflow_spec_id,
                                                           workflow_id=workflow_model.id,
                                                           name=file_name)
            if len(latest_files) < 1:
                raise ApiError("invalid_enum", "Unable to locate the lookup data file '%s'" % file_name)
            else:
                data_model = latest_files[0]

            lookup_model = LookupService.build_lookup_table(data_model, value_column, label_column,
                                                            workflow_model.workflow_spec_id, field_id)

        elif field.has_property(Task.PROP_LDAP_LOOKUP):
            lookup_model = LookupFileModel(workflow_spec_id=workflow_model.workflow_spec_id,
                                           field_id=field_id,
                                           is_ldap=True)
        else:
            raise ApiError("unknown_lookup_option",
                           "Lookup supports using spreadsheet options or ldap options, and neither "
                           "was provided.")
        db.session.add(lookup_model)
        db.session.commit()
        return lookup_model

    @staticmethod
    def build_lookup_table(data_model: FileDataModel, value_column, label_column, workflow_spec_id, field_id):
        """ In some cases the lookup table can be very large.  This method will add all values to the database
         in a way that can be searched and returned via an api call - rather than sending the full set of
          options along with the form.  It will only open the file and process the options if something has
          changed.  """
        xls = ExcelFile(data_model.data)
        df = xls.parse(xls.sheet_names[0])  # Currently we only look at the fist sheet.
        df = pd.DataFrame(df).replace({np.nan: None})
        if value_column not in df:
            raise ApiError("invalid_emum",
                           "The file %s does not contain a column named % s" % (data_model.file_model.name,
                                                                                value_column))
        if label_column not in df:
            raise ApiError("invalid_emum",
                           "The file %s does not contain a column named % s" % (data_model.file_model.name,
                                                                                label_column))

        lookup_model = LookupFileModel(workflow_spec_id=workflow_spec_id,
                                       field_id=field_id,
                                       file_data_model_id=data_model.id,
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
            db_query = db_query.filter(LookupDataModel.value == value)
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
                    new_terms = ["'%s'" % query]
                    for t in terms:
                        new_terms.append("%s:*" % t)
                    new_query = ' | '.join(new_terms)
                else:
                    new_query = "%s:*" % query

                # Run the full text query
                db_query = db_query.filter(LookupDataModel.label.match(new_query))
                # But hackishly order by like, which does a good job of
                # pulling more relevant matches to the top.
                db_query = db_query.order_by(desc(LookupDataModel.label.like("%" + query + "%")))

        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        result = db_query.limit(limit).all()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
        return result

    @staticmethod
    def _run_ldap_query(query, limit):
        users = LdapService.search_users(query, limit)

        """Converts the user models into something akin to the
        LookupModel in models/file.py, so this can be returned in the same way 
         we return a lookup data model."""
        user_list = []
        for user in users:
            user_list.append({"value": user['uid'],
                              "label": user['display_name'] + " (" + user['uid'] + ")",
                              "data": user
                              })
        return user_list
