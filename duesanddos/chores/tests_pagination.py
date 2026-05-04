from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from households.models import Household, HouseholdMember
from chores.models import Chore
import datetime

User = get_user_model()


class ChorePaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        self.client = Client()
        self.client.login(username="testuser", password="password123")

        self.household = Household.objects.create(name="House 1")
        self.profile = self.user.profile
        self.profile.active_household = self.household
        self.profile.save()

        HouseholdMember.objects.create(user=self.user, household=self.household)

        # Create some chores
        for i in range(15):
            Chore.objects.create(
                description=f"Chore {i}",
                household=self.household,
                created_by=self.user,
                repeat_type="ONE_TIME",
                due_date=datetime.date.today() + datetime.timedelta(days=i),
            )

    def test_pagination_all(self):
        """Test the 'all' option for chores per page."""
        response = self.client.get(reverse("chores_list"), {"chores_per_page": "all"})
        self.assertEqual(response.status_code, 200)
        # All 15 chores should be visible
        self.assertEqual(len(response.context["occurrences"].object_list), 15)

    def test_pagination_invalid_param(self):
        """Test falling back to default when an invalid per_page param is given."""
        response = self.client.get(
            reverse("chores_list"), {"chores_per_page": "invalid"}
        )
        self.assertEqual(response.status_code, 200)
        # Should fall back to 10
        self.assertEqual(len(response.context["occurrences"].object_list), 10)

    def test_pagination_all_empty(self):
        """Test 'all' when there are no chores."""
        Chore.objects.all().delete()
        response = self.client.get(reverse("chores_list"), {"chores_per_page": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["occurrences"].object_list), 0)
