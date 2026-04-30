from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser, Profile
import json


class CalendarViewPrefTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser", password="password123", email="test@example.com"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.client = Client()
        self.client.login(username="testuser", password="password123")
        self.url = reverse("update_calendar_view_pref")

    def test_update_view_pref_success(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"view": "timeGridWeek"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.default_calendar_view, "timeGridWeek")

    def test_update_view_pref_invalid_view(self):
        self.client.post(
            self.url,
            data=json.dumps({"view": "invalidView"}),
            content_type="application/json",
        )
        # Should NOT update if invalid
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.default_calendar_view, "dayGridMonth")

    def test_update_view_pref_get_fails(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test_update_view_pref_bad_json_returns_error(self):
        response = self.client.post(
            self.url,
            data="{not-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
