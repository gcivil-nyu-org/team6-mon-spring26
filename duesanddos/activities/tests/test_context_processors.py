from django.test import TestCase
from accounts.models import CustomUser, Profile
from activities.context_processors import activity_notifications
from activities.models import ActivityLog
from households.models import Household, HouseholdMember
from chores.models import Chore
from unittest.mock import MagicMock
from datetime import date, timedelta


class ContextProcessorTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="cp_user", password="testpassword", email="cp@a.com"
        )
        self.household = Household.objects.create(name="CP House")
        self.profile, _ = Profile.objects.update_or_create(
            user=self.user, defaults={"active_household": self.household}
        )
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )

    def test_anonymous_user(self):
        request = MagicMock()
        request.user.is_authenticated = False
        self.assertEqual(activity_notifications(request), {})

    def test_authenticated_user_no_household(self):
        request = MagicMock()
        request.user = self.user
        self.profile.active_household = None
        self.profile.save()
        context = activity_notifications(request)
        self.assertEqual(context, {})

    def test_authenticated_user_active_household(self):
        ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="LOGIN",
            details="Logged in",
        )
        chore = Chore.objects.create(
            description="Overdue chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            has_due_date=True,
            due_date=date.today() - timedelta(days=2),  # overdue
        )
        chore.assignees.add(self.user)

        request = MagicMock()
        request.user = self.user
        context = activity_notifications(request)

        self.assertEqual(len(context["recent_notifications"]), 1)
        self.assertEqual(context["notification_count"], 1)
