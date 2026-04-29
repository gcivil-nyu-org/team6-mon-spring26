import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from accounts.models import CustomUser as User
from activities.google_calendar import GoogleCalendarService


class GCalServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.build")
    def test_get_service_no_token(self, mock_build, mock_filter):
        """Test _get_service returns None if no social token exists."""
        mock_filter.return_value.select_related.return_value.first.return_value = None
        service = GoogleCalendarService(self.user)
        self.assertIsNone(service.service)
        mock_build.assert_not_called()

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    def test_get_service_no_refresh_token(self, mock_creds_class, mock_filter):
        """Test _get_service returns None if refresh needed but missing."""
        mock_token = MagicMock()
        mock_token.token_secret = None
        mock_token.expires_at = datetime.datetime.now() - datetime.timedelta(days=1)
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = None
        mock_creds_class.return_value = mock_creds

        service = GoogleCalendarService(self.user)
        self.assertIsNone(service.service)

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    def test_get_service_refresh_fail(self, mock_creds_class, mock_filter):
        """Test _get_service returns None if refresh fails."""
        mock_token = MagicMock()
        mock_token.token_secret = "refresh"
        mock_token.expires_at = datetime.datetime.now() - datetime.timedelta(days=1)
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh"
        mock_creds.refresh.side_effect = Exception("Refresh failed")
        mock_creds_class.return_value = mock_creds

        service = GoogleCalendarService(self.user)
        self.assertIsNone(service.service)

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    @patch("activities.google_calendar.build")
    def test_get_service_success_with_refresh(
        self, mock_build, mock_creds_class, mock_filter
    ):
        """Test _get_service successfully refreshes and builds service."""
        mock_token = MagicMock()
        mock_token.token_secret = "refresh"
        mock_token.token = "old_token"
        mock_token.expires_at = datetime.datetime.now() - datetime.timedelta(days=1)
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh"
        mock_creds.token = "new_token"
        mock_creds.expiry = datetime.datetime.now() + datetime.timedelta(days=1)
        mock_creds_class.return_value = mock_creds

        mock_build.return_value = "MockService"

        service = GoogleCalendarService(self.user)
        self.assertEqual(service.service, "MockService")
        self.assertEqual(mock_token.token, "new_token")
        mock_token.save.assert_called()

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    @patch("activities.google_calendar.build")
    def test_get_service_token_app_is_none_uses_settings(
        self, mock_build, mock_creds_class, mock_filter
    ):
        """Test _get_service falls back to settings when token.app is None."""
        mock_token = MagicMock()
        mock_token.app = None  # Force the settings-fallback branch
        mock_token.token_secret = "refresh"
        mock_token.expires_at = None  # Not expired
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_class.return_value = mock_creds

        mock_build.return_value = "MockServiceFromSettings"

        service = GoogleCalendarService(self.user)
        # Should still build successfully using settings fallback
        self.assertEqual(service.service, "MockServiceFromSettings")

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    @patch("activities.google_calendar.build")
    def test_build_event_body_one_time_no_due_date(
        self, mock_build, mock_creds_class, mock_filter
    ):
        """Test _build_event_body for ONE_TIME chore with no due date (line 176)."""
        from chores.models import Chore
        from households.models import Household

        household = Household.objects.create(name="Test HH")
        chore = Chore.objects.create(
            description="No due date chore",
            household=household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            has_due_date=False,
            due_time=None,
        )
        chore.assignees.add(self.user)

        mock_token = MagicMock()
        mock_token.app = None
        mock_token.token_secret = "refresh"
        mock_token.expires_at = None
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_class.return_value = mock_creds
        mock_build.return_value = MagicMock()

        gcal = GoogleCalendarService(self.user)
        body = gcal._build_event_body(chore)
        # Should contain "No due date" branch text
        self.assertIn("No due date", body["description"])
        self.assertIn("Any time", body["description"])

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    @patch("activities.google_calendar.build")
    def test_build_event_body_one_time_with_due_date(
        self, mock_build, mock_creds_class, mock_filter
    ):
        """Test _build_event_body for ONE_TIME chore with due date and time."""
        from chores.models import Chore
        from households.models import Household

        household = Household.objects.create(name="Test HH 2")
        chore = Chore.objects.create(
            description="Due date chore",
            household=household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            has_due_date=True,
            due_date=datetime.date.today(),
            due_time=datetime.time(14, 0),
        )
        chore.assignees.add(self.user)

        mock_token = MagicMock()
        mock_token.app = None
        mock_token.token_secret = "refresh"
        mock_token.expires_at = None
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_class.return_value = mock_creds
        mock_build.return_value = MagicMock()

        gcal = GoogleCalendarService(self.user)
        body = gcal._build_event_body(chore)
        self.assertIn("Due date:", body["description"])
        self.assertIn("2:00 PM", body["description"])

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    @patch("activities.google_calendar.build")
    def test_build_event_body_recurring_with_end_date_and_time(
        self, mock_build, mock_creds_class, mock_filter
    ):
        """Test _build_event_body for DAILY chore with end_date and due_time."""
        from chores.models import Chore
        from households.models import Household

        household = Household.objects.create(name="Test HH Recurring")
        chore = Chore.objects.create(
            description="Daily chore with time",
            household=household,
            created_by=self.user,
            repeat_type="DAILY",
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=7),
            due_time=datetime.time(9, 30),
        )
        chore.assignees.add(self.user)

        mock_token = MagicMock()
        mock_token.app = None
        mock_token.token_secret = "refresh"
        mock_token.expires_at = None
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_class.return_value = mock_creds
        mock_build.return_value = MagicMock()

        gcal = GoogleCalendarService(self.user)
        body = gcal._build_event_body(chore)
        # Should contain Starts: and due_time and end_date branches
        self.assertIn("Starts:", body["description"])
        self.assertIn("Ends:", body["description"])
        self.assertIn("9:30 AM", body["description"])

    @patch("activities.google_calendar.SocialToken.objects.filter")
    @patch("activities.google_calendar.Credentials")
    @patch("activities.google_calendar.build")
    def test_build_event_body_weekly_with_days(
        self, mock_build, mock_creds_class, mock_filter
    ):
        """Test _build_event_body for WEEKLY chore covers the day-map loop."""
        from chores.models import Chore
        from households.models import Household

        household = Household.objects.create(name="Test HH Weekly")
        chore = Chore.objects.create(
            description="Weekly chore",
            household=household,
            created_by=self.user,
            repeat_type="WEEKLY",
            start_date=datetime.date.today(),
            repeat_monday=True,
            repeat_wednesday=True,
            repeat_friday=True,
        )
        chore.assignees.add(self.user)

        mock_token = MagicMock()
        mock_token.app = None
        mock_token.token_secret = "refresh"
        mock_token.expires_at = None
        mock_filter.return_value.select_related.return_value.first.return_value = (
            mock_token
        )

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_class.return_value = mock_creds
        mock_build.return_value = MagicMock()

        gcal = GoogleCalendarService(self.user)
        body = gcal._build_event_body(chore)
        # Should show the repeats-on line with day names
        self.assertIn("Monday", body["description"])
        self.assertIn("Wednesday", body["description"])
        self.assertIn("Friday", body["description"])
