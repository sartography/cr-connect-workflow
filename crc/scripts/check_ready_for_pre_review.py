from crc.api.common import ApiError
from crc import app
from crc.scripts.script import Script


class CheckReadyForPreReview(Script):
    
    scripts = {}
    documents = {}

    def get_is_documents_ready(self, is_uva_irb_of_rec):
        doc_list = ['protocol_application_and_coversheet', 'data_security_plan', 'study_documents',
                    'consent_documents', 'drug_device_documents', 'ancillary_documents', 'form_documents']
        if not is_uva_irb_of_rec:
            doc_list = ['protocol_application_and_coversheet', 'data_security_plan', 'study_documents',
                        'consent_documents', 'drug_device_documents', 'ancillary_documents', 'form_documents',
                        'non_uva_irb']

        for doc in doc_list:
            get_workflow_status = self.scripts['get_workflow_status']
            workflow_status = get_workflow_status(doc)
            if workflow_status == "complete":
                is_documents_ready = True
            else:
                is_documents_ready = False
                break

        self.scripts['data_store_set'](type='study', key='sds_isDocumentsReady', value=is_documents_ready)
        return is_documents_ready

    def get_is_cto_required(self):
        study_info = self.scripts['study_info']
        # Get Documents
        documents = study_info('documents')
        self.documents = documents

        # Loop through CTO Review documents to determine
        # if any of them are required documents
        is_cto_required = False
        for key, d in documents.items():
            if d["workflow"] == "CTO Review" and d["required"]:
                is_cto_required = True
                break
        self.scripts['data_store_set'](type='study', key='sds_isCTORequired', value=is_cto_required)
        return is_cto_required

    def get_is_cto_ready(self, is_cto_required):

        if not is_cto_required:
            is_cto_ready = True
        else:
            get_workflow_status = self.scripts['get_workflow_status']
            workflow_status = get_workflow_status("cto_review")
            if workflow_status == "complete":
                is_cto_ready = True
            else:
                is_cto_ready = False

        self.scripts['data_store_set'](type='study', key='sds_isCTOReady', value=is_cto_ready)
        return is_cto_ready

    def get_is_department_chair_approval_ready(self):
        is_dept_chair_approval_ready = False
        # Check if Department Chair Approval is complete
        get_workflow_status = self.scripts['get_workflow_status']
        dept_chair_status = get_workflow_status("department_chair")
        if dept_chair_status == "complete":
            is_dept_chair_approval_ready = True

        self.scripts['data_store_set'](type='study',
                                       key='sds_isDeptChairApprovalReady',
                                       value=is_dept_chair_approval_ready)
        return is_dept_chair_approval_ready

    def is_zip_doc(self, is_uva_irb_of_rec, doc):
        if is_uva_irb_of_rec:
            if doc["zip_if_uva_irb"] == '√':
                is_zip_doc = True
            else:
                is_zip_doc = False
        else:
            if doc["zip_if_non_uva_irb"] == '√':
                is_zip_doc = True
            else:
                is_zip_doc = False
        return is_zip_doc

    def check_required_documents(self, is_uva_irb_of_rec):
        req_doc_cnt = 0
        is_required_document_reviews_complete = False

        rev_list = ["escro_approval", "gmec_approval", "grime_approval", "hire_approval", "ibc_approval",
                    "ids_approval", "ids_waiver", "laser_safety_approval", "mr_physicist_approval",
                    "new_medical_device_approval", "prc_approval", "prc_waiver", "rdrc_approval",
                    "ferpa_sbs_approval", "neonatal_icu_committee_approval"]

        data_store_set = self.scripts['data_store_set']
        get_workflow_status = self.scripts['get_workflow_status']

        # Loop through UVA Compliance documents to determine whether all
        # workflows associated with required documents have been completed
        for key, d in self.documents.items():
            if d['workflow_spec_id'] in rev_list:
                if self.is_zip_doc(is_uva_irb_of_rec, d) and d["required"]:
                    req_doc_cnt = req_doc_cnt + 1
                    workflow_status = get_workflow_status(d["workflow_spec_id"])
                    if workflow_status == "complete":
                        is_required_document_reviews_complete = True
                    else:
                        is_required_document_reviews_complete = False
                        data_store_set(type='study', key='sds_required_document_false', value=d['workflow_spec_id'])
                        break
        return req_doc_cnt, is_required_document_reviews_complete

    def get_is_compliance_reviews_ready(self, is_uva_irb_of_rec):
        data_store_set = self.scripts['data_store_set']
        is_compliance_reviews_ready = False
        is_dept_chair_approval_ready = self.get_is_department_chair_approval_ready()
        if is_dept_chair_approval_ready:
            # # Loop through UVA Compliance documents to determine whether all
            # # workflows associated with required documents have been completed
            # rev_list = ["escro_approval", "gmec_approval", "grime_approval", "hire_approval", "ibc_approval",
            #             "ids_approval", "ids_waiver", "laser_safety_approval", "mr_physicist_approval",
            #             "new_medical_device_approval", "prc_approval", "prc_waiver", "rdrc_approval",
            #             "ferpa_sbs_approval", "neonatal_icu_committee_approval"]
            # req_doc_cnt = 0
            #
            # get_workflow_status = self.scripts['get_workflow_status']
            # for key, d in self.documents.items():
            #     if d['workflow_spec_id'] in rev_list:
            #         # if is_uva_irb_of_rec:
            #         #     if d["zip_if_uva_irb"] == '√':
            #         #         is_zip_doc = True
            #         #     else:
            #         #         is_zip_doc = False
            #         # else:
            #         #     if d["zip_if_non_uva_irb"] == '√':
            #         #         is_zip_doc = True
            #         #     else:
            #         #         is_zip_doc = False
            #         if self.is_zip_doc(is_uva_irb_of_rec, d) and d["required"]:
            #             req_doc_cnt = req_doc_cnt + 1
            #             workflow_status = get_workflow_status(d["workflow_spec_id"])
            #             if workflow_status == "complete":
            #                 is_required_document_reviews_complete = True
            #             else:
            #                 is_required_document_reviews_complete = False
            #                 data_store_set(type='study', key='sds_required_document_false', value=d['workflow_spec_id'])
            #                 break
            req_doc_cnt, is_required_document_reviews_complete = self.check_required_documents(is_uva_irb_of_rec)
            if req_doc_cnt == 0 or is_required_document_reviews_complete:
                is_required_document_reviews_ready = True
            else:
                is_required_document_reviews_ready = False

            # If all Required Document Reviews are ready, check for those controlled by datastore
            if is_required_document_reviews_ready:
                # Check if Marketing Materials Approval is required
                # sdsMarMat_get = data_store_get(type='study', key="sdsMarMat", default=None)
                data_store_get = self.scripts['data_store_get']
                if data_store_get(type='study', key="sdsMarMat", default=None) == "true":
                    get_workflow_status = self.scripts['get_workflow_status']
                    workflow_status = get_workflow_status("marketing_materials_approval")
                    if workflow_status == "complete":
                        is_compliance_reviews_ready = True
                    else:
                        data_store_set(type='study', key='sds_marketing_materials_false', value=data_store_get(type='study', key="sdsMarMat", default=None))
                else:
                    is_compliance_reviews_ready = True
        data_store_set(type='study', key='sds_isComplianceReviewsReady', value=is_compliance_reviews_ready)
        return is_compliance_reviews_ready

    def get_description(self):
        return """Check whether this study is ready for pre-review.
        This requires (1)documents, (2)cto review (if required), and (3)compliance reviews."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        """This code used to be in the top_level_workflow, in the 'Check Ready for Pre-Review' Script Task.
        It was moved here while troubleshooting an issue displaying the IRB Submission column.

        Ultimately, I might move this to a call activity or sub process.
        We should at least break it into multiple tasks."""
        # TODO: move this all back into the top_level_workflow, into a call activity, sub process, etc
        is_uva_irb_of_record = args[0]
        # this is grey magic. I'm stealing code from the CustomBpmnScriptEngine class in workflow_processor.py
        # ultimately, this comes from the Script class we inherit from
        # this gives me access to all the scripts available to the workflows (in the scripts directory)
        scripts = self.generate_augmented_list(task, study_id, workflow_id)
        self.scripts = scripts
        is_documents_ready = self.get_is_documents_ready(is_uva_irb_of_record)
        is_cto_required = self.get_is_cto_required()
        is_cto_ready = self.get_is_cto_ready(is_cto_required)
        is_compliance_reviews_ready = self.get_is_compliance_reviews_ready(is_uva_irb_of_record)

        app.logger.info(f"CheckReadyForPreReview: is_documents_ready: {is_documents_ready}")
        
        return {'isDocumentsReady': is_documents_ready,
                'isCTORequired': is_cto_required,
                'isCTOReady': is_cto_ready,
                'isComplianceReviewsReady': is_compliance_reviews_ready
                }

