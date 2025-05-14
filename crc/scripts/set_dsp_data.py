from crc.api.common import ApiError
from crc.scripts.script import Script


class SaveDSPData(Script):

    def get_description(self):
        return """Saves data from the DSP forms to the data store.
        Which fields we save is determined by the dsp_form_variables reference file"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        doc_dict = self.get_dsp_form_variables_as_dictionary()
        for template_variable in doc_dict:
            if template_variable and template_variable in task.data:
                key = doc_dict[template_variable]['stored_variable']
                value = str(task.data[template_variable])
                task.data['data_store_set'](type='study',
                                            key=key,
                                            value=value)
