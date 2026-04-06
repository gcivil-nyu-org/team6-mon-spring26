from django.test import TestCase, RequestFactory
from django.urls import reverse
from accounts.models import CustomUser, Profile
from activities.views import sync_to_google, push_to_google_calendar
from households.models import Household, HouseholdMember
from chores.models import Chore
from unittest.mock import patch, MagicMock


class ActivitiesViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUser.objects.create_user(
            username="act_user", password="testpassword", email="act@a.com"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.client.login(username="act_user", password="testpassword")

        self.household = Household.objects.create(name="Act House")
        self.profile.active_household = self.household
        self.profile.save()
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )

    @patch("activities.views.GoogleCalendarService")
    def test_calendar_view_authenticated(self, MockGoogleCalendarService):
        mock_service = MagicMock()
        mock_service.service = True
        MockGoogleCalendarService.return_value = mock_service

        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)

    def test_calendar_events_api_no_household(self):
        self.profile.active_household = None
        self.profile.save()
        response = self.client.get(reverse("calendar_events_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("activities.views.GoogleCalendarService")
    def test_sync_to_google(self, MockGoogleCalendarService):
        mock_service = MagicMock()
        mock_service.service = True
        mock_service.sync_chore.return_value = {"id": "123"}
        MockGoogleCalendarService.return_value = mock_service

        chore = Chore.objects.create(
            description="Sync GCal",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
        )

        request = self.factory.post("/fake/")
        request.user = self.user

        response = sync_to_google(request, chore.id, "2026-04-06")
        self.assertEqual(response.status_code, 200)

    @patch("activities.views.GoogleCalendarService")
    def test_push_to_google_calendar(self, MockGoogleCalendarService):
        mock_service = MagicMock()
        mock_service.service = True
        mock_service.sync_chore.return_value = {"id": "123"}
        MockGoogleCalendarService.return_value = mock_service

        chore = Chore.objects.create(
            description="Push GCal",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
        )

        request = self.factory.post("/fake/")
        request.user = self.user

        result = push_to_google_calendar(request, {"chore": chore})
        self.assertEqual(result, "123")

    def test_activity_feed_view(self):
        response = self.client.get(reverse("activity_feed"))
        self.assertEqual(response.status_code, 200)
