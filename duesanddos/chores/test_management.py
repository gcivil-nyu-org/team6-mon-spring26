from django.core.management import call_command
from django.test import TestCase
from accounts.models import CustomUser
from households.models import Household
from chores.models import Chore
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from io import StringIO


class SyncGcalOverduesTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="mgmt_user", password="123", email="mgmt@a.com"
        )
        self.household = Household.objects.create(name="Mgmt House")

        # Create an overdue chore
        self.chore = Chore.objects.create(
            description="Overdue stuff",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() + timedelta(days=2),
        )
        self.chore.assignees.add(self.user)

    @patch("chores.management.commands.sync_gcal_overdues.GoogleCalendarService")
    def test_sync_gcal_overdues_command(self, MockGcal):
        mock_service = MagicMock()
        mock_service.service = True
        mock_service.mark_occurrence_overdue.return_value = True
        MockGcal.return_value = mock_service

        out = StringIO()
        call_command("sync_gcal_overdues", stdout=out)
        self.assertIn("Sync complete", out.getvalue())

        # Should be called once or twice depending on how many occurrences are overdue
        mock_service.mark_occurrence_overdue.assert_called()
