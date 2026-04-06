from django.test import TestCase
from accounts.models import CustomUser
from households.models import Household
from chores.models import Chore, ChoreCompletion, ChoreSkip
from unittest.mock import patch
from datetime import date


class ChoreSignalsTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="sig_mgmt", password="123", email="sig_mgmt@a.com"
        )
        self.household = Household.objects.create(name="Sig House 2")
        self.chore = Chore.objects.create(
            description="Test signal chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            due_date=date.today(),
        )
        self.chore.assignees.add(self.user)
        from .models import ChoreGoogleEvent

        ChoreGoogleEvent.objects.create(
            chore=self.chore, user=self.user, google_event_id="test_id"
        )

    @patch("chores.signals.GoogleCalendarService")
    def test_sync_chore_to_gcal_signal(self, MockGcal):
        self.chore.description = "Updated chore"
        self.chore.save()
        MockGcal.assert_called()

    @patch("chores.signals.GoogleCalendarService")
    def test_delete_chore_from_gcal_task_signal(self, MockGcal):
        self.chore.delete()
        MockGcal.assert_called()

    @patch("chores.signals.GoogleCalendarService")
    def test_update_completion_gcal_task_signal(self, MockGcal):
        ChoreCompletion.objects.create(
            chore=self.chore, occurrence_date=date.today(), completed_by=self.user
        )
        MockGcal.assert_called()

    @patch("chores.signals.GoogleCalendarService")
    def test_update_skip_gcal_task_signal(self, MockGcal):
        ChoreSkip.objects.create(
            chore=self.chore, occurrence_date=date.today(), skipped_by=self.user
        )
        MockGcal.assert_called()
