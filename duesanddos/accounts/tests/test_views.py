import tempfile
import shutil
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings
from django.urls import reverse
from allauth.socialaccount.models import SocialApp
from accounts.models import CustomUser, Profile
from households.models import Household

TEST_PASSWORD = "TestPass123!"
NEW_PASSWORD = "NewSecure456!"
SMALL_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00"
    b"\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff\x21\xf9\x04\x00\x00"
    b"\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44"
    b"\x01\x00\x3b"
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AuthAndProfileTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username="testuser", password=TEST_PASSWORD)
        # Create a SocialApp for Google so the profile template's
        # {% provider_login_url 'google' %} tag doesn't raise DoesNotExist.
        site = Site.objects.get_current()
        social_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="test-client-id",
            secret="test-secret",
        )
        social_app.sites.add(site)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_profile_view_get(self):
        url = reverse("profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/edit_profile.html")

    def test_profile_view_post_save_profile(self):
        url = reverse("profile")
        data = {
            "save_profile": "1",
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "email": self.user.email,
            "username": self.user.username,
            "bio": "New Bio",
            "notifications_enabled": True,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, url)

    def test_profile_view_post_change_password(self):
        url = reverse("profile")
        data = {
            "change_password": "1",
            "old_password": TEST_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_profile_view_post_invalid(self):
        url = reverse("profile")
        response = self.client.post(url, {"something_else": "1"})
        self.assertEqual(response.status_code, 200)

    def test_logout_get(self):
        url = reverse("logout")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/logout.html")

    def test_delete_account_view_get(self):
        url = reverse("delete_account")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("profile"))

    def test_delete_account_view_post_wrong_password(self):
        url = reverse("delete_account")
        response = self.client.post(url, {"confirmation": "wrongpass"})
        self.assertRedirects(response, reverse("profile"))

    def test_delete_account_view_post_no_password_wrong_word(self):
        self.user.set_unusable_password()
        self.user.save()
        self.client.force_login(self.user)
        url = reverse("delete_account")
        response = self.client.post(url, {"confirmation": "delete"})
        self.assertRedirects(response, reverse("profile"))

    def test_delete_account_view_post_correct_password(self):
        url = reverse("delete_account")
        response = self.client.post(url, {"confirmation": TEST_PASSWORD})
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(CustomUser.objects.filter(username="testuser").exists())

    def test_dashboard_view_get(self):
        url = reverse("dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard.html")

    def test_dashboard_valid_dates(self):
        h = Household.objects.create(name="Test HH", invite_code="TEST2")
        from households.models import HouseholdMember

        HouseholdMember.objects.create(user=self.user, household=h)
        self.profile.active_household = h
        self.profile.save()
        url = reverse("dashboard")
        response = self.client.get(
            url, {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        self.assertEqual(response.status_code, 200)

    def test_dashboard_household_does_not_exist(self):
        self.profile.active_household_id = 99999
        self.profile.save()
        url = reverse("dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.active_household)

    def test_dashboard_invalid_dates(self):
        h = Household.objects.create(name="Test HH", invite_code="TEST1")
        from households.models import HouseholdMember

        HouseholdMember.objects.create(user=self.user, household=h)
        self.profile.active_household = h
        self.profile.save()
        url = reverse("dashboard")
        response = self.client.get(
            url, {"start_date": "invalid", "end_date": "invalid"}
        )
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        url = reverse("logout")
        self.client.post(url)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)


class RegisterViewTests(TestCase):
    def test_register_get(self):
        url = reverse("register")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_register_post(self):
        url = reverse("register")
        data = {
            "username": "newuser",
            "firstName": "New",
            "lastName": "User",
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "confirmPassword": "StrongPass123!",
        }
        self.client.post(url, data)
        self.assertTrue(CustomUser.objects.filter(username="newuser").exists())


class StaticPageViewTests(TestCase):
    def test_static_pages(self):
        for name in ["faq", "terms", "privacy"]:
            url = reverse(name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
