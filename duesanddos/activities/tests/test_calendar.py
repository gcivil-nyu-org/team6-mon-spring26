import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser as User
from accounts.models import Profile
from chores.models import Chore
from households.models import Household


class CalendarApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")

        # Setup household context
        self.household = Household.objects.create(name="Test Home")
        self.profile = Profile.objects.create(
            user=self.user, active_household=self.household
        )

    def test_calendar_api_returns_chores(self):
        """Test if the API correctly fetches a chore occurrence."""
        Chore.objects.create(
            description="Test Calendar Chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            has_due_date=True,
            due_date=datetime.date.today(),
        )

        response = self.client.get(reverse("calendar_events_api"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Calendar Chore")
