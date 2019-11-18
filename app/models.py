from django.db import models
from viewflow.models import Process


class CRConnectProcess(Process):
    study_name = models.CharField(verbose_name="Study Name", max_length=1000)
    pi_computing_id = models.EmailField(verbose_name="Principal Investigator's computing ID")
    pi_experience_description = models.TextField(verbose_name="Describe the PI's experience")
    will_have_contract = models.BooleanField(verbose_name="Study will have a contract")
    responsible_organization = models.CharField(verbose_name="Responsible Organization", max_length=1000)
    study_title = models.CharField(verbose_name="Study Title", max_length=1000)
    study_abstract = models.TextField(verbose_name="Study Abstract", max_length=1000)
    study_type = models.CharField(
        verbose_name="Study Type",
        choices=[
            ("full_board", "Full Board"),
            ("expedited", "Expedited"),
            ("non_engaged", "Non-Engaged"),
            ("exempt", "Exempt"),
            ("non_human", "Non-Human"),
            ("emergency_use", "Emergency Use"),
        ],
        max_length=1000
    )
    department_chair_signature = models.FileField(
        verbose_name="Department Chair Signature",
        help_text="Signed PDF provided by Docusign"
    )



