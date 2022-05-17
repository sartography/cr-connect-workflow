import hashlib
import io
import os
import random
import string

import pandas as pd
from github import Github, GithubObject, UnknownObjectException
from uuid import UUID
from lxml import etree

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from crc import session, app
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.file import FileType, FileDataModel, FileModel, FileModel
from crc.models.workflow import WorkflowModel
from crc.services.cache_service import cache
from crc.services.user_service import UserService
import re


def camel_to_snake(camel):
    """
    make a camelcase from a snakecase
    with a few things thrown in - we had a case where
    we were parsing a spreadsheet and using the headings as keys in an object
    one of the headings was "Who Uploads?"
    """
    camel = camel.strip()
    camel = re.sub(' ', '', camel)
    camel = re.sub('?', '', camel)
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel).lower()


class UserFileService(object):

    @staticmethod
    @cache
    def is_workflow_review(workflow_spec_id):
        files = session.query(FileModel).filter(FileModel.workflow_spec_id==workflow_spec_id).all()
        review = any([f.is_review for f in files])
        return review

    @staticmethod
    def update_irb_code(file_id, irb_doc_code):
        """Create a new file and associate it with the workflow
        Please note that the irb_doc_code MUST be a known file in the irb_documents.xslx reference document."""
        file_model = session.query(FileModel)\
            .filter(FileModel.id == file_id).first()
        if file_model is None:
            raise ApiError("invalid_file_id",
                           "When updating the irb_doc_code for a file, that file_id must already exist "
                           "This file_id is not found in the database '%d'" % file_id)

        file_model.irb_doc_code = irb_doc_code
        session.commit()
        return True

    @staticmethod
    def add_workflow_file(workflow_id, irb_doc_code, task_spec_name, name, content_type, binary_data):
        # Verify the extension
        file_extension = UserFileService.get_extension(name)
        if file_extension not in FileType._member_names_:
            raise ApiError('unknown_extension',
                           'The file you provided does not have an accepted extension:' +
                           file_extension, status_code=404)
        # NOTE: Do not archive files with the same doc code, as it is possible to upload many files of the same type.
        md5_checksum = UUID(hashlib.md5(binary_data).hexdigest())
        try:
            user_uid = UserService.current_user().uid
        except ApiError as ae:
            user_uid = None
        new_file_model = FileModel(
            name=name,
            type=FileType[file_extension].value,
            content_type=content_type,
            workflow_id=workflow_id,
            task_spec=task_spec_name,
            irb_doc_code=irb_doc_code,
            md5_hash=md5_checksum,
            data=binary_data,
            user_uid=user_uid,
            archived=False,
            size=len(binary_data)
        )
        session.add(new_file_model)
        session.commit()
        session.flush()
        return new_file_model

    @staticmethod
    def get_workflow_files(workflow_id):
        """Returns all the file models associated with a running workflow."""
        return session.query(FileModel).filter(FileModel.workflow_id == workflow_id).\
            order_by(FileModel.id).all()

    @staticmethod
    def get_extension(file_name):
        basename, file_extension = os.path.splitext(file_name)
        return file_extension.lower().strip()[1:]

    def update_file(self, file_model, binary_data, content_type):
        # We do not update files, we delete (archive) the old one and add a new one
        self.delete_file(file_model.id)
        return file_model

    @staticmethod
    def get_files_for_study(study_id, irb_doc_code=None, include_archived=False):
        query = session.query(FileModel).\
                join(WorkflowModel).\
                filter(WorkflowModel.study_id == study_id)
        if not include_archived:
            # Current documents have an archived value of False
            query = query.filter(FileModel.archived == False)
        if irb_doc_code is not None:
            query = query.filter(FileModel.irb_doc_code == irb_doc_code)
        return query.order_by(desc(FileModel.date_modified)).all()

    @staticmethod
    def get_files(workflow_id=None, name=None, irb_doc_code=None):
        if workflow_id is not None:
            query = session.query(FileModel).filter_by(workflow_id=workflow_id)
            if irb_doc_code:
                query = query.filter_by(irb_doc_code=irb_doc_code)

            if name:
                query = query.filter_by(name=name)

            query = query.order_by(FileModel.id)

            results = query.all()
            return results

    @staticmethod
    def get_workflow_data_files(workflow_id=None):
        """Returns all the FileDataModels related to a running workflow -
        So these are the latest data files that were uploaded or generated
        that go along with this workflow.  Not related to the spec in any way"""
        file_models = UserFileService.get_files(workflow_id=workflow_id)
        return file_models

    @staticmethod
    def get_file_data(file_id: int, version: int = None):
        """Returns the file data with the given version, or the lastest file, if version isn't provided."""
        query = session.query(FileDataModel) \
            .filter(FileDataModel.file_model_id == file_id)
        if version:
            query = query.filter(FileDataModel.version == version)
        else:
            query = query.order_by(desc(FileDataModel.date_created))
        return query.first()

    @staticmethod
    def delete_file_data_stores(file_id):
        try:
            session.query(DataStoreModel).filter_by(file_id=file_id).delete()
        except IntegrityError as ie:
            session.rollback()
            app.logger.info(f"Failed to delete file data stores. Original error is {ie}")
            raise ApiError('failed_delete_data_stores', f"Unable to delete file data stores for file {file_id}.")
        finally:
            session.commit()

    def delete_file(self, file_id):
        self.delete_file_data_stores(file_id)
        # We archive files so users can access previous versions
        document_model = session.query(FileModel).filter_by(id=file_id).first()
        document_model.archived = True
        session.commit()

    @staticmethod
    def dmn_from_spreadsheet(ss_data):

        def _get_random_string(length):
            return ''.join(
                [random.choice(string.ascii_letters + string.digits) for n in range(length)])

        def _row_has_value(values):
            for value_item in values:
                if not pd.isnull(value_item):
                    return True
            return False

        df = pd.read_excel(io.BytesIO(ss_data.read()), header=None)

        xml_ns = "https://www.omg.org/spec/DMN/20191111/MODEL/"
        dmndi_ns = "https://www.omg.org/spec/DMN/20191111/DMNDI/"
        dc_ns = "http://www.omg.org/spec/DMN/20180521/DC/"
        dmndi = "{%s}" % dmndi_ns
        dc = "{%s}" % dc_ns
        nsmap = {None: xml_ns, 'dmndi': dmndi_ns, 'dc': dc_ns}

        root = etree.Element("definitions",
                             id="Definitions",
                             name="DRD",
                             namespace="http://camunda.org/schema/1.0/dmn",
                             nsmap=nsmap,
                             )

        decision_name = df.iat[0, 1]
        decision_id = df.iat[1, 1]
        decision = etree.SubElement(root, "decision",
                                    id=decision_id,
                                    name=decision_name
                                    )
        decision_table = etree.SubElement(decision, 'decisionTable', id='decisionTable_1')
        input_output = df.iloc[2][1:]
        count = 1
        input_count = 1
        output_count = 1
        for item in input_output:
            if item == 'Input':
                label = df.iloc[3, count]
                input_ = etree.SubElement(decision_table, 'input', id=f'input_{input_count}', label=label)
                type_ref = df.iloc[5, count]
                input_expression = etree.SubElement(input_, 'inputExpression', id=f'inputExpression_{input_count}',
                                                    typeRef=type_ref)
                expression = df.iloc[4, count]
                expression_text = etree.SubElement(input_expression, 'text')
                expression_text.text = expression

                input_count += 1
            elif item == 'Output':
                label = df.iloc[3, count]
                name = df.iloc[4, count]
                type_ref = df.iloc[5, count]
                decision_table.append(etree.Element('output', id=f'output_{output_count}',
                                                    label=label, name=name, typeRef=type_ref))
                output_count += 1
            elif item == 'Annotation':
                break
            count += 1

        row = 6
        column_count = count
        while row < df.shape[0]:
            column = 1
            row_values = df.iloc[row].values[1:column_count]
            if _row_has_value(row_values):
                rando = _get_random_string(7).lower()
                rule = etree.SubElement(decision_table, 'rule', id=f'DecisionRule_{rando}')

                i = 1
                while i < input_count:
                    input_entry = etree.SubElement(rule, 'inputEntry', id=f'UnaryTests_{_get_random_string(7)}')
                    text_element = etree.SubElement(input_entry, 'text')
                    text_element.text = str(df.iloc[row, column]) if not pd.isnull(df.iloc[row, column]) else ''
                    i += 1
                    column += 1
                i = 1
                while i < output_count:
                    output_entry = etree.SubElement(rule, 'outputEntry', id=f'LiteralExpression_{_get_random_string(7)}')
                    text_element = etree.SubElement(output_entry, 'text')
                    text_element.text = str(df.iloc[row, column]) if not pd.isnull(df.iloc[row, column]) else ''
                    i += 1
                    column += 1

                description = etree.SubElement(rule, 'description')
                text = df.iloc[row, column] if not pd.isnull(df.iloc[row, column]) else ''
                description.text = text

            row += 1

        dmndi_root = etree.SubElement(root, dmndi + "DMNDI")
        dmndi_diagram = etree.SubElement(dmndi_root, dmndi + "DMNDiagram")
        # rando = _get_random_string(7).lower()
        dmndi_shape = etree.SubElement(dmndi_diagram, dmndi + "DMNShape",
                                       dmnElementRef=decision_id)
        bounds = etree.SubElement(dmndi_shape, dc + "Bounds",
                                  height='80', width='180', x='100', y='100')

        prefix = b'<?xml version="1.0" encoding="UTF-8"?>'
        dmn_file = prefix + etree.tostring(root)

        return dmn_file
