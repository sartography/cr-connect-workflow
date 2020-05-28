import logging

from pandas import ExcelFile
from sqlalchemy import func, desc
from sqlalchemy.sql.functions import GenericFunction

from crc import db
from crc.api.common import ApiError
from crc.models.api_models import Task
from crc.models.file import FileDataModel, LookupFileModel, LookupDataModel
from crc.services.file_service import FileService
from crc.services.ldap_service import LdapService

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
    def lookup(spiff_task, field, query, limit):
        """Executes the lookup for the given field."""
        if field.type != Task.FIELD_TYPE_AUTO_COMPLETE:
            raise ApiError.from_task("invalid_field_type",
                                          "Field '%s' must be an autocomplete field to use lookups." % field.label,
                                          task=spiff_task)

        # If this field has an associated options file, then do the lookup against that field.
        if field.has_property(Task.PROP_OPTIONS_FILE):
            lookup_table = LookupService.get_lookup_table(spiff_task, field)
            return LookupService._run_lookup_query(lookup_table, query, limit)
        # If this is a ldap lookup, use the ldap service to provide the fields to return.
        elif field.has_property(Task.PROP_LDAP_LOOKUP):
            return LookupService._run_ldap_query(query, limit)
        else:
            raise ApiError.from_task("unknown_lookup_option",
                                     "Lookup supports using spreadsheet options or ldap options, and neither was"
                                     "provided.")

    @staticmethod
    def get_lookup_table(spiff_task, field):
        """ Checks to see if the options are provided in a separate lookup table associated with the
        workflow, and if so, assures that data exists in the database, and return a model than can be used
        to locate that data.

        Returns:  an array of LookupData, suitable for returning to the api.
        """
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
            data_model = FileService.get_workflow_file_data(spiff_task.workflow, file_name)
            lookup_model = LookupService.get_lookup_table_from_data_model(data_model, value_column, label_column)
            return lookup_model

    @staticmethod
    def get_lookup_table_from_data_model(data_model: FileDataModel, value_column, label_column):
        """ In some cases the lookup table can be very large.  This method will add all values to the database
         in a way that can be searched and returned via an api call - rather than sending the full set of
          options along with the form.  It will only open the file and process the options if something has
          changed.  """

        lookup_model = db.session.query(LookupFileModel) \
            .filter(LookupFileModel.file_data_model_id == data_model.id) \
            .filter(LookupFileModel.value_column == value_column) \
            .filter(LookupFileModel.label_column == label_column).first()

        if not lookup_model:
            xls = ExcelFile(data_model.data)
            df = xls.parse(xls.sheet_names[0])  # Currently we only look at the fist sheet.
            if value_column not in df:
                raise ApiError("invalid_emum",
                               "The file %s does not contain a column named % s" % (data_model.file_model.name,
                                                                                    value_column))
            if label_column not in df:
                raise ApiError("invalid_emum",
                               "The file %s does not contain a column named % s" % (data_model.file_model.name,
                                                                                    label_column))

            lookup_model = LookupFileModel(label_column=label_column, value_column=value_column,
                                           file_data_model_id=data_model.id)

            db.session.add(lookup_model)
            for index, row in df.iterrows():
                lookup_data = LookupDataModel(lookup_file_model=lookup_model,
                                              value=row[value_column],
                                              label=row[label_column],
                                              data=row.to_json())
                db.session.add(lookup_data)
            db.session.commit()

        return lookup_model

    @staticmethod
    def _run_lookup_query(lookup_file_model, query, limit):
        db_query = LookupDataModel.query.filter(LookupDataModel.lookup_file_model == lookup_file_model)

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
            #ORDER BY name LIKE concat('%', ticker, '%') desc, rank DESC

#            db_query = db_query.order_by(desc(func.full_text.ts_rank(
#                func.to_tsvector(LookupDataModel.label),
#                func.to_tsquery(query))))
        from sqlalchemy.dialects import postgresql
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        result = db_query.limit(limit).all()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
        return result

    @staticmethod
    def _run_ldap_query(query, limit):
        users = LdapService().search_users(query, limit)

        """Converts the user models into something akin to the
        LookupModel in models/file.py, so this can be returned in the same way 
         we return a lookup data model."""
        user_list = []
        for user in users:
            user_list.append( {"value": user.uid,
                                "label": user.display_name + " (" + user.uid + ")",
                                "data": user.__dict__
                               })
        return user_list