from django.test import TestCase
from accounts.models import CustomUser
from activities.google_calendar import GoogleCalendarService
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from unittest.mock import patch, MagicMock
from chores.models import Chore
from households.models import Household
from datetime import date


class GoogleCalendarServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="gcal_user", password="password", email="gcal@a.com"
        )

        self.app = SocialApp.objects.create(
            provider="google", name="Google", client_id="123", secret="456"
        )
        self.account = SocialAccount.objects.create(
            user=self.user, provider="google", uid="user@gmail.com"
        )
        self.token = SocialToken.objects.create(
            app=self.app, account=self.account, token="tok", token_secret="sec"
        )

        self.household = Household.objects.create(name="GC House")
        self.chore = Chore.objects.create(
            description="Google chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            due_date=date.today(),
        )
        self.chore.assignees.add(self.user)
        from chores.models import ChoreGoogleEvent

        ChoreGoogleEvent.objects.create(
            chore=self.chore, user=self.user, google_event_id="test_id"
        )

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_service_init_success(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds
        MockBuild.return_value = MagicMock()

        service = GoogleCalendarService(self.user)
        self.assertIsNotNone(service.service)

    def test_service_init_no_token(self):
        user_no_token = CustomUser.objects.create_user(
            username="no_token", email="notok@a.com"
        )
        service = GoogleCalendarService(user_no_token)
        self.assertIsNone(service.service)

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_sync_chore(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds

        mock_service = MagicMock()
        MockBuild.return_value = mock_service
        service = GoogleCalendarService(self.user)

        events = MagicMock()
        mock_service.events.return_value = events
        events.insert().execute.return_value = {"id": "ev1"}

        result = service.sync_chore(self.chore)
        self.assertIsNotNone(result)

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_mark_occurrence_done(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds

        mock_service = MagicMock()
        events = MagicMock()
        mock_service.events.return_value = events
        MockBuild.return_value = mock_service

        events.get().execute.return_value = {"id": "ev123"}

        service = GoogleCalendarService(self.user)
        service.mark_occurrence_done(self.chore, date.today())

        events.update.assert_called_once()
