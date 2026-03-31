import tempfile
import shutil
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import CustomUser, Profile

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

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_profile_view_get(self):
        url = reverse("profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/edit_profile.html")

    def test_dashboard_view_get(self):
        url = reverse("dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard.html")

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
