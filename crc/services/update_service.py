
# loop over all the categories in the database
# assure we have a directory with the correct name
# assure it contains a valid json file called categories.json
import json
import os
import pathlib
import re
import shutil

from crc import db, app
from crc.models.file import FileModel
from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowSpecCategoryModelSchema, WorkflowSpecModelSchema, \
    WorkflowSpecModel

LIBRARY_SPECS = "Library Specs"
STAND_ALONE_SPECS = "Stand Alone"
MASTER_SPECIFICATION = "Master Specification"
REFERENCE_FILES = "Reference Files"
SPECIAL_FOLDERS = [LIBRARY_SPECS, MASTER_SPECIFICATION, REFERENCE_FILES]
CAT_JSON_FILE = "category.json"
WF_JSON_FILE = "workflow.json"


base_dir = '../SPECS'
app_root = app.root_path
path = os.path.join(app_root, '..', 'SPECS')
CAT_SCHEMA = WorkflowSpecCategoryModelSchema()
SPEC_SCHEMA = WorkflowSpecModelSchema()


def remove_all_json_files(path):
    for json_file in pathlib.Path(path).glob('*.json'):
        os.remove(json_file)


def update_workflows_for_category(path, schemas, category_id):
    for schema in schemas:
        orig_path = os.path.join(path, schema.display_name)
        new_path = os.path.join(path, schema.id)
        if (os.path.exists(orig_path)):
            os.rename(orig_path, new_path)
        update_spec(new_path, schema, category_id)


def update_spec(path, schema, category_id):
        json_data = SPEC_SCHEMA.dump(schema)
        remove_all_json_files(path)

        # Fixup the libraries
        lib_ids = list(map(lambda x: x['id'], json_data['libraries']))

        # calculate the primary process id, and primary file name
        file = db.session.query(FileModel).\
            filter(FileModel.workflow_spec_id == schema.id).\
            filter(FileModel.primary == True).first()
        if(file):
            json_data['primary_file_name'] = file.name
            json_data['primary_process_id'] = file.primary_process_id
        else:
            print("This workflow doesn't have a primary process:", json_data)

        json_data['category_id'] = category_id
        json_data.pop('category', None)
        json_data.pop('parents', None)
        if json_data['library'] is None:
            json_data['library'] = False

        json_data['libraries'] = lib_ids
        if not os.path.exists(path):
            os.makedirs(path)
        json_file_name = os.path.join(path, 'workflow.json')
        with open(json_file_name, 'w') as wf_handle:
            json.dump(json_data, wf_handle, indent=4)

# Clean up json files
remove_all_json_files(path)

# Clean up libraries
lib_path = os.path.join(path, LIBRARY_SPECS)
remove_all_json_files(lib_path)
workflows = db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.library == True)
update_workflows_for_category(lib_path, workflows, "")

# Clean up reference Files
ref_path = os.path.join(path, REFERENCE_FILES)
old_ref_path = os.path.join(path,'Reference')
if os.path.exists(old_ref_path):
    os.rename(old_ref_path, ref_path)
remove_all_json_files(ref_path)

# Clean up the master spec
tlw = os.path.join(path, MASTER_SPECIFICATION, "Top Level Workflow")
master_path = os.path.join(path, MASTER_SPECIFICATION)
if os.path.exists(tlw):
    for src_file in pathlib.Path(tlw).glob('*.*'):
        shutil.copy(src_file, master_path)
remove_all_json_files(master_path)
schema = db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.is_master_spec == True).first()
update_spec(master_path, schema, "")


# Fix all the categories
categories = db.session.query(WorkflowSpecCategoryModel).all()
for category in categories:
    json_data = CAT_SCHEMA.dump(category)
    orig_path = os.path.join(path, category.display_name)
    new_name = re.sub(r'[^A-Za-z0-9]', '_', category.display_name).lower()
    new_path = os.path.join(path, new_name)
    json_data['id'] = new_name
    if (os.path.exists(orig_path)):
        os.rename(orig_path, new_path)

    remove_all_json_files(new_path)
    json_file_name = os.path.join(new_path, 'category.json')
    with open(json_file_name, 'w') as f_handle:
        json.dump(json_data, f_handle, indent=4)

    workflows = db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.category_id == category.id)
    update_workflows_for_category(new_path, workflows, new_name)