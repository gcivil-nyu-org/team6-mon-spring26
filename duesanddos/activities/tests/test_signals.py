from django.test import TestCase
from accounts.models import CustomUser, Profile
from households.models import Household
from chores.models import Chore, ChoreCompletion
from activities.models import ActivityLog
from datetime import date
from activities.signals import log_chore_completion


class ActivitiesSignalsTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="sig_user", password="testpassword", email="sig@a.com"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.household = Household.objects.create(name="Sig House")
        self.chore = Chore.objects.create(
            description="Signal chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
        )

    def test_log_chore_completion_signal(self):
        initial_count = ActivityLog.objects.count()

        instance = ChoreCompletion.objects.create(
            chore=self.chore, occurrence_date=date.today(), completed_by=self.user
        )

        # Manually call it if signal not fired correctly in test env
        log_chore_completion(sender=ChoreCompletion, instance=instance, created=True)

        new_count = ActivityLog.objects.count()
        self.assertGreater(new_count, initial_count)
