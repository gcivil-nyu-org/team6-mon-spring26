from django.test import TestCase
from accounts.models import CustomUser
from activities.google_calendar import GoogleCalendarService
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from unittest.mock import patch, MagicMock
from chores.models import Chore
from households.models import Household
from datetime import date, datetime
from django.utils import timezone


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
        self.gcal_patcher = patch("chores.signals.GoogleCalendarService")
        self.gcal_patcher.start()

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

    def tearDown(self):
        self.gcal_patcher.stop()

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

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_service_init_success_with_expiry(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = timezone.now()
        mock_creds.expired = False
        mock_creds.token = "new_token_str"
        MockCredentials.return_value = mock_creds
        MockBuild.return_value = MagicMock()

        self.token.expires_at = timezone.now()
        self.token.save()

        service = GoogleCalendarService(self.user)
        self.assertIsNotNone(service.service)

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_service_init_normalizes_naive_expiry(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = datetime.now()
        mock_creds.expired = False
        mock_creds.token = "tok"
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
    def test_sync_chore_creates_new_event_when_sync_record_missing(
        self, MockCredentials, MockBuild
    ):
        from chores.models import ChoreGoogleEvent

        ChoreGoogleEvent.objects.filter(chore=self.chore, user=self.user).delete()

        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds

        mock_service = MagicMock()
        events = MagicMock()
        mock_service.events.return_value = events
        events.insert().execute.return_value = {"id": "ev-new"}
        MockBuild.return_value = mock_service

        service = GoogleCalendarService(self.user)
        result = service.sync_chore(self.chore)

        self.assertEqual(result["id"], "ev-new")
        events.insert.assert_any_call(
            calendarId="primary", body=service._build_event_body(self.chore)
        )
        self.assertTrue(
            ChoreGoogleEvent.objects.filter(
                chore=self.chore, user=self.user, google_event_id="ev-new"
            ).exists()
        )

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

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_daily_and_weekly_recurrence_rules(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds

        service = GoogleCalendarService(self.user)

        # Test DAILY with end date
        self.chore.repeat_type = "DAILY"
        self.chore.end_date = date.today()
        daily_rule = service._get_recurrence_rule(self.chore)
        self.assertTrue(daily_rule[0].startswith("RRULE:FREQ=DAILY"))
        self.assertIn("UNTIL=", daily_rule[0])

        # Test WEEKLY with various days
        self.chore.repeat_type = "WEEKLY"
        self.chore.repeat_monday = True
        self.chore.repeat_tuesday = True
        self.chore.repeat_wednesday = True
        self.chore.repeat_thursday = True
        self.chore.repeat_friday = True
        self.chore.repeat_saturday = True
        self.chore.repeat_sunday = True
        weekly_rule = service._get_recurrence_rule(self.chore)
        self.assertIn("BYDAY=MO,TU,WE,TH,FR,SA,SU", weekly_rule[0])

        self.chore.repeat_monday = False
        self.chore.repeat_tuesday = False
        self.chore.repeat_wednesday = False
        self.chore.repeat_thursday = False
        self.chore.repeat_friday = False
        self.chore.repeat_saturday = False
        self.chore.repeat_sunday = False
        self.assertIsNone(service._get_recurrence_rule(self.chore))

    def test_build_event_body_edges(self):
        service = GoogleCalendarService(self.user)
        self.chore.repeat_type = "DAILY"
        self.chore.start_date = None

        # Test missing start_date and daily recurrence building
        body = service._build_event_body(self.chore)
        self.assertIn("recurrence", body)
        self.assertEqual(body["recurrence"][0], "RRULE:FREQ=DAILY")

        # Test status prefix
        body2 = service._build_event_body(self.chore, status_prefix="✅ DONE")
        self.assertTrue(body2["summary"].startswith("✅ DONE"))

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_mark_occurrence_done_recurring(self, MockCredentials, MockBuild):
        self.chore.repeat_type = "DAILY"
        self.chore.save()
        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds

        mock_service = MagicMock()
        events = MagicMock()
        mock_service.events.return_value = events
        MockBuild.return_value = mock_service

        # Mock instances return
        events.instances().execute.return_value = {
            "items": [
                {
                    "id": "inst1",
                    "summary": "Existing",
                    "start": {"date": date.today().isoformat()},
                }
            ]
        }

        service = GoogleCalendarService(self.user)
        res = service.mark_occurrence_done(self.chore, date.today())
        self.assertTrue(res)
        events.update.assert_called_once()

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_mark_occurrence_overdue(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds

        mock_service = MagicMock()
        events = MagicMock()
        mock_service.events.return_value = events
        MockBuild.return_value = mock_service

        # Single event
        events.get().execute.return_value = {"id": "ev123", "summary": "Cool Chore"}
        service = GoogleCalendarService(self.user)
        res = service.mark_occurrence_overdue(self.chore, date.today())
        self.assertTrue(res)
        events.update.assert_called_once()

        # Recurring event
        self.chore.repeat_type = "DAILY"
        events.instances().execute.return_value = {
            "items": [
                {
                    "id": "inst2",
                    "summary": "Existing",
                    "start": {"date": date.today().isoformat()},
                }
            ]
        }
        res2 = service.mark_occurrence_overdue(self.chore, date.today())
        self.assertTrue(res2)

    @patch("activities.google_calendar.build")
    @patch("activities.google_calendar.Credentials")
    def test_delete_chore_event(self, MockCredentials, MockBuild):
        mock_creds = MagicMock()
        mock_creds.expiry = None
        mock_creds.expired = False
        MockCredentials.return_value = mock_creds

        mock_service = MagicMock()
        events = MagicMock()
        mock_service.events.return_value = events
        MockBuild.return_value = mock_service

        service = GoogleCalendarService(self.user)
        res = service.delete_chore_event(self.chore)
        self.assertTrue(res)
        events.delete.assert_called_once()
