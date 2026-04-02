from django.test import TestCase
from django.urls import reverse
from accounts.adapters import CustomAccountAdapter, CustomSocialAccountAdapter


class AdapterTests(TestCase):
    def test_custom_account_adapter(self):
        adapter = CustomAccountAdapter()
        url = adapter.get_login_redirect_url(request=None)
        self.assertEqual(url, reverse("dashboard"))

    def test_custom_social_account_adapter(self):
        adapter = CustomSocialAccountAdapter()
        url = adapter.get_connect_redirect_url(request=None, socialaccount=None)
        self.assertEqual(url, reverse("dashboard"))

    def test_social_is_auto_signup_allowed(self):
        adapter = CustomSocialAccountAdapter()
        is_allowed = adapter.is_auto_signup_allowed(request=None, sociallogin=None)
        self.assertFalse(is_allowed)
