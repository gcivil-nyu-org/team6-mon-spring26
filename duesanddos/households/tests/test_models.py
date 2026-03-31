from django.test import TestCase
from accounts.models import CustomUser
from households.models import Household, HouseholdMember

TEST_PASSWORD = "TestPass123!"


class HouseholdModelTests(TestCase):
    def test_str_returns_name(self):
        hh = Household.objects.create(name="Test House")
        self.assertEqual(str(hh), "Test House")

    def test_default_fields_are_empty(self):
        hh = Household.objects.create(name="Empty House")
        self.assertEqual(hh.description, "")
        self.assertEqual(hh.default_rules, "")

    def test_fields_can_be_saved(self):
        hh = Household.objects.create(
            name="Filled House",
            description="A nice house",
            default_rules="No shoes inside",
        )
        hh.refresh_from_db()
        self.assertEqual(hh.description, "A nice house")
        self.assertEqual(hh.default_rules, "No shoes inside")


class HouseholdMemberModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="memtest",
            email="memtest@example.com",
            password=TEST_PASSWORD,
        )
        self.hh = Household.objects.create(name="Member House")
        self.member = HouseholdMember.objects.create(
            user=self.user, household=self.hh, role="Admin"
        )

    def test_str_returns_formatted_string(self):
        expected = "memtest - Member House (Admin)"
        self.assertEqual(str(self.member), expected)
