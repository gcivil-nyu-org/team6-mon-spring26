from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount
from allauth.account.signals import user_signed_up
from accounts.models import Profile

User = get_user_model()


class SignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)

    @patch("accounts.signals.requests.get")
    def test_fetch_gmail_photo_success(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image content"
        mock_get.return_value = mock_response

        # Setup social account
        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            extra_data={"picture": "http://example.com/photo.jpg"},
        )

        # Triger the signal
        user_signed_up.send(sender=User, request=None, user=self.user)

        # Check if avatar was saved
        # Note: We need to refresh from DB
        self.profile.refresh_from_db()
        self.assertTrue(bool(self.profile.avatar))
        self.assertEqual(self.profile.avatar.read(), b"fake image content")

    @patch("accounts.signals.requests.get")
    def test_fetch_gmail_photo_no_social_account(self, mock_get):
        user_signed_up.send(sender=User, request=None, user=self.user)
        mock_get.assert_not_called()

    @patch("accounts.signals.requests.get")
    def test_fetch_gmail_photo_no_picture_url(self, mock_get):
        SocialAccount.objects.create(user=self.user, provider="google", extra_data={})
        user_signed_up.send(sender=User, request=None, user=self.user)
        mock_get.assert_not_called()

    @patch("accounts.signals.requests.get")
    def test_fetch_gmail_photo_failure(self, mock_get):
        # Setup mock response for failure
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            extra_data={"picture": "http://example.com/photo.jpg"},
        )

        # Should not crash
        user_signed_up.send(sender=User, request=None, user=self.user)

        self.profile.refresh_from_db()
        self.assertFalse(bool(self.profile.avatar))

    @patch("builtins.print")
    @patch("accounts.signals.requests.get")
    def test_fetch_gmail_photo_exception_handled(self, mock_get, mock_print):
        mock_get.side_effect = Exception("Network error")

        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            extra_data={"picture": "http://example.com/photo.jpg"},
        )

        # Should not crash
        user_signed_up.send(sender=User, request=None, user=self.user)
        self.assertFalse(bool(self.profile.avatar))
        mock_print.assert_not_called()

    @patch("accounts.signals.requests.get")
    def test_fetch_gmail_photo_existing_avatar(self, mock_get):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.profile.avatar = SimpleUploadedFile(
            "existing.jpg", b"old image", content_type="image/jpeg"
        )
        self.profile.save()

        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            extra_data={"picture": "http://example.com/photo.jpg"},
        )

        user_signed_up.send(sender=User, request=None, user=self.user)
        mock_get.assert_not_called()
