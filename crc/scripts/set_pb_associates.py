from crc.api.common import ApiError
from crc.scripts.script import Script


class SetPBAssociates(Script):

    def add_sub_investigators(self, subs, pb_create_uid, task):
        for k in subs.keys():
            sub = subs.get(k)
            # the study creator always gets access and emails
            if sub["uid"] == pb_create_uid:
                sub["access"] = True
                sub["emails"] = True
            # else:
            #     sub["access"] = subpb[k]["access"]
            #     sub["emails"] = subpb[k]["emails"]
            task.data['update_study_associate'](uid=sub.uid,
                                                access=sub.access,
                                                send_email=sub.emails,
                                                role=sub.label)

    def add_primary_coordinators(self, pcs, pb_create_uid, pcpb, is_pbc_pc, task):
        for k in pcs.keys():
            pc = pcs.get(k)
            # TODO: what is is_pbc_pc?
            if is_pbc_pc:
                if pc["uid"] == pb_create_uid:
                    pc["access"] = True
                    pc["emails"] = True
                else:
                    pc["access"] = pcpb[k]["access"]
                    pc["emails"] = pcpb[k]["emails"]
            task.data['update_study_associate'](uid=pc.uid, access=pc.access, send_email=pc.emails, role=pc.label)

    def add_dept_chair(self, dc, pi, pb_create_uid, task):
        # If the dept chair is also PI, use access/email values from the PI
        if dc.uid == pi.uid:
            access = pi.access
            emails = pi.emails
            # but, the study creator always gets access and emails
            if dc.uid == pb_create_uid:
                access = True
                emails = True
            task.data['update_study_associate'](uid=dc.uid, access=access, send_email=emails, role=dc.label)

        else:
            # if not the PI, check if they are the study creator
            if dc.uid == pb_create_uid:
                dc.access = True
                dc.emails = True
            task.data['update_study_associate'](uid=dc.uid, access=dc.access, send_email=dc.emails, role=dc.label)

    def add_principal_investigator(self, pi, pb_create_uid, task):
        if pi.uid != pb_create_uid:
            task.data['update_study_associate'](uid=pi.uid, access=pi.access, send_email=pi.emails, role=pi.label)
        else:
            task.data['update_study_associate'](uid=pi.uid, access=True, send_email=True, role=pi.label)

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        """This code used to be in the Personnel workflow, in the 'Set PB Associates' Script Task.
        It was moved here while troubleshooting an issue adding associated users who also created the study.

        Ultimately, I might move this to a call activity or sub process.
        We should at least break it into multiple tasks."""
        # TODO: move this all back into the Personnel workflow, into a call activity, sub process, etc

        valid_ap_count = task.data.get('valid_ap_count', 0)
        AP = task.data.get('AP', [])  # additional personnel
        cnt_subs = task.data.get('cnt_subs', 0)
        subs = task.data.get('subs', {})
        # is_pbc_subs = task.data.get('is_pbc_subs', False)
        pb_create_uid = task.data.get('pb_create_uid', None)
        # subpb = task.data.get('subpb', {})
        cnt_pcs = task.data.get('cnt_pcs', 0)
        pcs = task.data.get('pcs', {})
        dc = task.data.get('dc', {})
        pi = task.data.get('pi', {})
        is_pbc_pc = task.data.get('is_pbc_pc', False)
        pcpb = task.data.get('pcpb', {})

        if valid_ap_count > 0:
            for a in AP:
                if a["display_name"] != "Not Found":
                    task.data['update_study_associate'](uid=a.cid, access=a.access, send_email=a.emails, role=a.role)

        # Add Sub-Investigators
        if cnt_subs != 0:
            self.add_sub_investigators(subs, pb_create_uid, task)

        # Add Primary Coordinators
        if cnt_pcs != 0:
            self.add_primary_coordinators(pcs, pb_create_uid, pcpb, is_pbc_pc, task)

        # Add Department Chair
        self.add_dept_chair(dc, pi, pb_create_uid, task)

        # Add Principle Investigator
        self.add_principal_investigator(pi, pb_create_uid, task)
