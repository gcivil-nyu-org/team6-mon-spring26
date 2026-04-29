import datetime
from django.test import TestCase
from accounts.models import CustomUser as User
from activities.google_calendar import GoogleCalendarService
from unittest.mock import patch, MagicMock

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
        mock_filter.return_value.select_related.return_value.first.return_value = mock_token
        
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
        mock_filter.return_value.select_related.return_value.first.return_value = mock_token
        
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
    def test_get_service_success_with_refresh(self, mock_build, mock_creds_class, mock_filter):
        """Test _get_service successfully refreshes and builds service."""
        mock_token = MagicMock()
        mock_token.token_secret = "refresh"
        mock_token.token = "old_token"
        mock_token.expires_at = datetime.datetime.now() - datetime.timedelta(days=1)
        mock_filter.return_value.select_related.return_value.first.return_value = mock_token
        
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
