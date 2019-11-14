from django.test import TestCase
from app.models import CRConnectProcess
from app.flows import CRConnectFlow


class CRConnectProcessTestCase(TestCase):
    def setUp(self):
        CRConnectProcess.objects.create(text="Process 1", approved=False)
        CRConnectProcess.objects.create(text="Process 2", approved=True)

    def test_processes_are_created(self):
        """Processes are created and their attributes are initialized properly"""
        p1 = CRConnectProcess.objects.get(text="Process 1")
        p2 = CRConnectProcess.objects.get(text="Process 2")
        self.assertEqual(p1.approved, False)
        self.assertEqual(p2.approved, True)

    def test_processes_are_modified(self):
        """Process attributes can be modified"""
        CRConnectProcess.objects.update_or_create(
            text="Process 1",
            defaults={"text": "Process Renamed 1", "approved": True}
        )

        CRConnectProcess.objects.update_or_create(
            text="Process 2",
            defaults={"text": "Process Renamed 2", "approved": False}
        )

        p1 = CRConnectProcess.objects.get(approved=True)
        p2 = CRConnectProcess.objects.get(approved=False)
        self.assertEqual(p1.text, "Process Renamed 1")
        self.assertEqual(p2.text, "Process Renamed 2")
