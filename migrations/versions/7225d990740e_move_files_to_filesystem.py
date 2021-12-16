"""Move files to filesystem

Revision ID: 7225d990740e
Revises: 44dd9397c555
Create Date: 2021-12-14 10:52:50.785342

"""
import json

from alembic import op
import sqlalchemy as sa
from crc import app, db, session
# from crc.models.file import FileModel, FileDataModel
# from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowSpecCategoryModel, WorkflowSpecCategoryModelSchema
# import os
#
# from crc.services.file_service import FileService


# revision identifiers, used by Alembic.
revision = '7225d990740e'
down_revision = '44dd9397c555'
branch_labels = None
depends_on = None


class TempCategoryModel(db.Model):
    __tablename__ = 'temp_category'
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String)
    display_order = db.Column(db.Integer)
    admin = db.Column(db.Boolean)


class TempSpecModel(db.Model):
    __tablename__ = 'temp_spec'
    id = db.Column(db.String, primary_key=True)
    display_name = db.Column(db.String)
    display_order = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('workflow_spec_category.id'), nullable=True)
    category = db.relationship("WorkflowSpecCategoryModel")
    is_master_spec = db.Column(db.Boolean, default=False)
    standalone = db.Column(db.Boolean, default=False)
    library = db.Column(db.Boolean, default=False)

#
# def process_directory(directory):
#     files = []
#     directories = []
#     directory_items = os.scandir(directory)
#     for item in directory_items:
#         if item.is_dir():
#             directories.append(item)
#         elif item.is_file():
#             files.append(item)
#
#     return files, directories
#
#
# def process_workflow_spec(json_file, directory):
#     file_path = os.path.join(directory, json_file)
#
#     with open(file_path, 'r') as f_open:
#         data = f_open.read()
#         data_obj = json.loads(data)
#         workflow_spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.display_name==data_obj['display_name']).first()
#         if not workflow_spec_model:
#             workflow_spec_model = WorkflowSpecModel(display_name=data_obj['display_name'],
#                                                     description=data_obj['description'],
#                                                     is_master_spec=data_obj['is_master_spec'],
#                                                     category_id=data_obj['category_id'],
#                                                     display_order=data_obj['display_order'],
#                                                     standalone=data_obj['standalone'],
#                                                     library=data_obj['library'])
#             session.add(workflow_spec_model)
#
#     # session.commit()
#
#     print(f'process_workflow_spec: workflow_spec_model: {workflow_spec_model}')
#     return workflow_spec_model
#
#
# def process_workflow_spec_files():
#     pass
#
#
# def process_category(json_file, root):
#     print(f'process_category: json_file: {json_file}')
#     file_path = os.path.join(root, json_file)
#
#     with open(file_path, 'r') as f_open:
#         data = f_open.read()
#         data_obj = json.loads(data)
#         category = session.query(TempCategoryModel).filter(
#             TempCategoryModel.display_name == data_obj['display_name']).first()
#         if not category:
#             category = TempCategoryModel(display_name=data_obj['display_name'],
#                                                       display_order=data_obj['display_order'],
#                                                       admin=data_obj['admin'])
#             session.add(category)
#         else:
#             category.display_order = data_obj['display_order']
#             category.admin = data_obj['admin']
#         # print(data)
#         print(f'process_category: category: {category}')
#
#     session.commit()
#     return category
#
#
# def process_workflow_spec_directory(spec_directory):
#     print(f'process_workflow_spec_directory: {spec_directory}')
#     files, directories = process_directory(spec_directory)
#
#     for file in files:
#         print(f'process_workflow_spec_directory: file: {file}')
#
#
# def process_category_directory(category_directory):
#     print(f'process_category_directory: {category_directory}')
#     files, directories = process_directory(category_directory)
#
#     for file in files:
#         if file.name.endswith('.json'):
#             workflow_spec = process_workflow_spec(file, category_directory)
#
#     for workflow_spec_directory in directories:
#         directory_path = os.path.join(category_directory, workflow_spec_directory)
#         process_workflow_spec_directory(directory_path)
#
#
# def process_root_directory(root_directory):
#
#     files, directories = process_directory(root_directory)
#     for file in files:
#         if file.name.endswith('.json'):
#             category_model = process_category(file, root_directory)
#
#     for directory in directories:
#         directory_path = os.path.join(root_directory, directory)
#         process_category_directory(directory_path)
#
#
# def update_file_metadata_from_filesystem(root_directory):
#     process_root_directory(root_directory)


def temp_tables():
    op.create_table('temp_category',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('display_name', sa.String(), nullable=True),
                    sa.Column('display_order', sa.String(), nullable=True),
                    sa.Column('admin', sa.Boolean(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )

    op.create_table('temp_spec',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('display_name', sa.String()),
                    sa.Column('description', sa.Text()),
                    sa.Column('is_master_spec', sa.Boolean(), nullable=True),
                    sa.Column('category_id', sa.Integer(), nullable=True),
                    sa.Column('category', sa.Integer(), nullable=True),
                    sa.Column('display_order', sa.Integer(), nullable=True),
                    sa.Column('standalone', sa.Boolean(), nullable=True),
                    sa.Column('library', sa.Boolean(), nullable=True),
                    sa.ForeignKeyConstraint(['category_id'], ['temp_category.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_foreign_key(None, 'temp_spec', 'temp_category', ['category'], ['id'])


def upgrade():
    files = session.query(FileModel).all()
    for file in files:
        if file.archived is not True:
            FileService.write_file_to_system(file)
    print('upgrade: done: ')


def downgrade():

    temp_tables()

    print(f'temp category count: {session.query(TempCategoryModel).count()}')

    # Update DB from the filesystem
    SYNC_FILE_ROOT = os.path.join(app.root_path, '..', 'files')
    update_file_metadata_from_filesystem(SYNC_FILE_ROOT)

    print('downgrade: ')
