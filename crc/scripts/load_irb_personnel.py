from crc.api.common import ApiError
from crc.scripts.script import Script


class LoadIRBPersonnel(Script):

    @staticmethod
    def clean_record(record):
        if 'display' in record:
            del record["display"]
        if 'unique' in record:
            del record["unique"]
        if 'telephone_number' in record:
            del record["telephone_number"]
        if 'date_cached' in record:
            del record["date_cached"]

    def get_pb_create_uid(self, study_id, current_user_uid, task):
        user_studies = task.data['get_user_studies'](current_user_uid)
        user_study_ids = [x["STUDYID"] for x in user_studies]
        is_current_user_pb_create = study_id in user_study_ids
        # If the current user did create the study in PB, store their uid in pb_create_uid
        if is_current_user_pb_create:
            pb_create_uid = current_user_uid
        else:
            pb_create_uid = "xxxxx"
        return pb_create_uid

    @staticmethod
    def get_is_pbc_subs(investigators, pb_create_uid):
        for k in investigators.keys():
            if k.startswith('SI'):
                if investigators[k]["user_id"] == pb_create_uid:
                    return True
        return False

    def process_investigators(self, investigators, is_pbc_subs, pb_create_uid):
        subs = {}
        subpb = {}
        subx = {}
        for k in investigators.keys():
            if k[:2] == 'SI':  # k.startswith() can fail here, so we use ==
                investigator = investigators.get(k)
                if investigator.get('uid', None) is not None:
                    subs[k] = investigator
                    self.clean_record(subs[k])
                    if is_pbc_subs and investigator['uid'] != pb_create_uid:
                        subpb[k] = investigator
                else:
                    subx[k] = investigator
        return subs, subpb, subx

    def process_pi_dc(self, obj, pb_create_uid):
        invalid_uid = True
        is_type = False
        if obj is not None:
            self.clean_record(obj)
            if obj.get('uid', None) is not None:
                invalid_uid = False
                obj['E0'] = {}
                if obj['uid'] == pb_create_uid:
                    is_type = True
        return invalid_uid, is_type

    def process_other_investigators(self, investigators, is_pbc_pc, pb_create_uid):
        pcs = {}
        pcpb = {}
        pcx = {}
        for k in investigators.keys():
            if k in ['SC_I', 'SC_II', 'IRBC', 'DC'] or k.startswith('AS_C'):
                investigator = investigators.get(k)
                if investigator.get('uid', None) is not None:
                    pcs[k] = investigator
                    self.clean_record(pcs[k])

                    if is_pbc_pc and investigator['uid'] != pb_create_uid:
                        pcpb[k] = investigator
                else:
                    pcx[k] = investigator
                    self.clean_record(pcx[k])
        return pcs, pcpb, pcx

    def get_description(self):
        return """Process the associated users from PB for use in the Personnel workflow"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        """This code used to be in the Personnel workflow, in the 'Load IRB Personnel' Script Task.
        It was moved here while troubleshooting an issue adding associated users who also created the study.

        Ultimately, I might move this to a call activity or sub process.
        We should at least break it into multiple tasks."""
        # TODO: move this all back into the Personnel workflow, into a call activity, sub process, etc

        current_user = task.data.get('current_user')

        # Clear Datastores
        if task.data['data_store_get'](type='study', key="sdsPI_ComputingID", default='') != '':
            task.data['data_store_set'](type='study', key="sdsPI_ComputingID", value='')
        if task.data['data_store_get'](type='study', key="sdsDC_ComputingID", default='') != '':
            task.data['data_store_set'](type='study', key="sdsDC_ComputingID", value='')

        # Determine if Current User created study in Protocol Builder
        pb_create_uid = self.get_pb_create_uid(study_id, current_user["uid"], task)

        # Load IRB Personnel
        investigators = task.data['study_info']('investigators')

        # Principal Investigator
        pi = investigators.get('PI', None)
        if pi is not None:
            has_pi = True
            pi_invalid_uid, is_pbc_pi = self.process_pi_dc(pi, pb_create_uid)
            if pi_invalid_uid:
                pi['uid'] = ''
        else:
            pi_invalid_uid = True
            is_pbc_pi = False
            has_pi = False

        # Department Chair
        dc = investigators.get('DEPT_CH', None)
        if dc is not None:
            has_dc = True
            dc_invalid_uid, is_pbc_dc = self.process_pi_dc(dc, pb_create_uid)
            if dc_invalid_uid:
                dc['uid'] = ''
        else:
            dc_invalid_uid = True
            is_pbc_dc = False
            has_dc = False

        # Primary Coordinators
        is_pbc_pc = pb_create_uid in [investigators[k]["user_id"] for k in investigators.keys() if
                                      k in ['SC_I', 'SC_II', 'IRBC']]
        pcs, pcpb, pcx = self.process_other_investigators(investigators, is_pbc_pc, pb_create_uid)

        # Check to see if any invalid uids
        pcs_invalid_uid = len(pcx.keys()) > 0  # boolean
        cnt_pcs = len(pcs.keys()) if len(pcs.keys()) > 0 else 0
        cnt_pcpb = len(pcpb.keys()) if len(pcpb.keys()) > 0 else 0

        is_pbc_subs = self.get_is_pbc_subs(investigators, pb_create_uid)
        subs, subpb, subx = self.process_investigators(investigators, is_pbc_subs, pb_create_uid)

        subs_invalid_uid = len(subx.keys()) > 0
        cnt_subs = len(subs.keys()) if len(subs.keys()) > 0 else 0
        cnt_subpb = len(subpb.keys()) if len(subpb.keys()) > 0 else 0

        task.data['data_store_set'](type='study', key="sdsCnt_Subs", value=cnt_subs)
        task.data['data_store_set'](type='study', key="sdsCnt_Subpb", value=cnt_subpb)

        data = {'pi': pi,
                'dc': dc,
                'pcs': pcs,
                'pcpb': pcpb,
                'subs': subs,
                'subpb': subpb,
                'subx': subx,
                'is_pbc_pi': is_pbc_pi,
                'is_pbc_dc': is_pbc_dc,
                'is_pbc_pc': is_pbc_pc,
                'is_pbc_subs': is_pbc_subs,
                'cnt_pcs': cnt_pcs,
                'cnt_pcpb': cnt_pcpb,
                'cnt_subs': cnt_subs,
                'cnt_subpb': cnt_subpb,
                'hasPI': has_pi,
                'hasDC': has_dc,
                'pi_invalid_uid': pi_invalid_uid,
                'dc_invalid_uid': dc_invalid_uid,
                'pcs_invalid_uid': pcs_invalid_uid,
                'subs_invalid_uid': subs_invalid_uid,
                'pb_create_uid': pb_create_uid,
                'pcx': pcx,
                }

        return data
