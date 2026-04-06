from django.test import TestCase
from django.contrib.auth import get_user_model
from households.models import Household
from activities.models import ActivityLog


class ActivityLogModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="activityp", email="act@example.com", password="Pass123!"
        )
        self.household = Household.objects.create(name="Act House")
        self.log = ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="EXPENSE_ADDED",
            details="Added test expense",
        )

    def test_activity_log_creation(self):
        self.assertEqual(self.log.action, "EXPENSE_ADDED")
        self.assertIn("Added test expense", self.log.details)
        self.assertTrue(self.log.id)

    def test_activity_log_ordering(self):
        log2 = ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="EXPENSE_DELETED",
            details="Deleted test expense",
        )
        logs = ActivityLog.objects.all()
        # Ordering is -timestamp, so log2 should be first
        self.assertEqual(logs[0], log2)

    def test_activity_log_str(self):
        expected_str = (
            f"{self.user.username} - {self.log.action} at {self.log.timestamp}"
        )
        self.assertEqual(str(self.log), expected_str)
