from viewflow import flow, frontend
from viewflow.base import this, Flow
from viewflow.flow.views import CreateProcessView, UpdateProcessView

from .models import CRConnectProcess


@frontend.register
class CRConnectFlow(Flow):
    process_class = CRConnectProcess

    start = (
        flow.Start(
            CreateProcessView,
            fields=[
                "study_name",
                "pi_computing_id",
            ]
        ).Permission(
            auto_create=True
        ).Next(this.provide_computing_id)
    )

    provide_computing_id = (
        flow.AbstractJob(this.lookup_contact_information)
            .Next(this.describe_pi_experience)
    )

    describe_pi_experience = (
        flow.View(
            UpdateProcessView,
            fields=[
                "pi_experience_description",
                "responsible_organization",
            ]
        ).Next(this.select_responsible_organization)
    )

    select_responsible_organization = (
        flow.AbstractJob(this.lookup_organization_information)
            .Next(this.enter_title)
    )

    enter_title = (
        flow.View(
            UpdateProcessView,
            fields=[
                "study_title",
                "study_abstract",
                "study_type",
                "will_have_contract",
            ]
        ).Next(this.check_will_have_contract)
    )

    check_will_have_contract = (
        flow.If(lambda activation: activation.process.will_have_contract)
        .Then(this.request_signature_from_department_chair)
        .Else(this.end)
    )

    request_signature_from_department_chair = (
        flow.Handler(
            this.provide_department_chair_signature
        ).Next(this.end)
    )

    end = flow.End()

    def provide_department_chair_signature(self, activation):
        print(activation.process.study_name)

    def lookup_contact_information(self, activation):
        print(activation.process.pi_computing_id)



