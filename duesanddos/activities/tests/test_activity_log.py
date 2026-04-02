from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import Profile
from households.models import Household, HouseholdMember
from activities.models import ActivityLog

User = get_user_model()
TEST_PASSWORD = "TestPass123!"


class ActivityLogViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="activitytester", email="act@example.com", password=TEST_PASSWORD
        )
        self.household = Household.objects.create(name="Activity House")
        self.profile = Profile.objects.create(
            user=self.user, active_household=self.household
        )
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        self.client.login(username="activitytester", password=TEST_PASSWORD)
        self.url = reverse("activity_log")

    def test_activity_log_view_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/activity.html")

    def test_activity_log_view_redirect_if_no_household(self):
        self.profile.active_household = None
        self.profile.save()
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("household_settings"))

    def test_activity_log_filtering(self):
        ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="EXPENSE_ADDED",
            details="Added X",
        )
        ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="PAYMENT_SETTLED",
            details="Settled Y",
        )

        # Filter action
        response = self.client.get(self.url, {"action": "EXPENSE_ADDED"})
        self.assertEqual(len(response.context["activities"]), 1)
        self.assertEqual(response.context["activities"][0].action, "EXPENSE_ADDED")

        # Filter date range
        today = timezone.now().date()
        start = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        response = self.client.get(self.url, {"start_date": start, "end_date": end})
        self.assertEqual(response.status_code, 200)

        # Invalid date fallback
        response = self.client.get(
            self.url, {"start_date": "invalid-date", "end_date": "2026-99-99"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["start_date"], timezone.now().date().replace(day=1)
        )
