from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from accounts.models import Profile
from households.models import Household, HouseholdMember

User = get_user_model()
TEST_PASSWORD = "TestPass123!"


class ExpenseProCoverageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password=TEST_PASSWORD
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com", password=TEST_PASSWORD
        )
        self.household = Household.objects.create(name="Test House")
        self.profile = Profile.objects.create(
            user=self.user, active_household=self.household
        )
        Profile.objects.create(user=self.other, active_household=self.household)
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        HouseholdMember.objects.create(
            user=self.other, household=self.household, role="Member"
        )
        self.client.login(username="testuser", password=TEST_PASSWORD)
        self.url = reverse("add_expense_pro")

    def test_add_expense_pro_no_active_household_error(self):
        self.profile.active_household = None
        self.profile.save()
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "10",
                "payer": str(self.user.id),
                "split_type": "EQUAL",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Please select an active household first.", messages)

    def test_add_expense_pro_missing_title_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "",
                "amount": "10",
                "payer": str(self.user.id),
                "split_type": "EQUAL",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Please enter a title for the expense.", messages)

    def test_add_expense_pro_missing_amount_or_participants_error(self):
        # Missing amount
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "",
                "payer": str(self.user.id),
                "split_type": "EQUAL",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn(
            "Please provide an amount and select at least one person.", messages
        )
        # Missing participants
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "10",
                "payer": str(self.user.id),
                "split_type": "EQUAL",
                "participants": [],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn(
            "Please provide an amount and select at least one person.", messages
        )

    def test_add_expense_pro_invalid_amount_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "invalid",
                "payer": str(self.user.id),
                "split_type": "EQUAL",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Please enter a valid total amount (numbers only).", messages)

    def test_add_expense_pro_negative_amount_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "-10",
                "payer": str(self.user.id),
                "split_type": "EQUAL",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Total amount must be greater than 0.", messages)

    def test_add_expense_pro_invalid_payer_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "10",
                "payer": "9999",
                "split_type": "EQUAL",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Selected payer was not found.", messages)

    def test_add_expense_pro_payer_not_in_household_error(self):
        stranger = User.objects.create_user(
            username="stranger", email="stranger@ex.com", password=TEST_PASSWORD
        )
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "10",
                "payer": str(stranger.id),
                "split_type": "EQUAL",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Selected payer is not part of the active household.", messages)

    def test_add_expense_pro_invalid_participants_error(self):
        stranger = User.objects.create_user(
            username="stranger2", email="stranger2@ex.com", password=TEST_PASSWORD
        )
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "10",
                "payer": str(self.user.id),
                "split_type": "EQUAL",
                "participants": [str(stranger.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn(
            "One or more selected participants are invalid or deactivated.", messages
        )

    def test_add_expense_pro_invalid_split_type_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "10",
                "payer": str(self.user.id),
                "split_type": "MAGIC",
                "participants": [str(self.user.id)],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Invalid split type.", messages)

    def test_add_expense_pro_percent_split_invalid_percent_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "100",
                "payer": str(self.user.id),
                "split_type": "PERCENT",
                "participants": [str(self.user.id)],
                f"percent_{self.user.id}": "invalid",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn(
            f"Please enter a valid percentage for {self.user.username}.", messages
        )

    def test_add_expense_pro_percent_split_negative_percent_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "100",
                "payer": str(self.user.id),
                "split_type": "PERCENT",
                "participants": [str(self.user.id)],
                f"percent_{self.user.id}": "-10",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Percentages cannot be negative.", messages)

    def test_add_expense_pro_percent_split_not_100_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "100",
                "payer": str(self.user.id),
                "split_type": "PERCENT",
                "participants": [str(self.user.id)],
                f"percent_{self.user.id}": "90",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Percentages must add up to exactly 100.", messages)

    def test_add_expense_pro_amount_split_invalid_amount_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "100",
                "payer": str(self.user.id),
                "split_type": "AMOUNT",
                "participants": [str(self.user.id)],
                f"amount_{self.user.id}": "invalid",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn(
            f"Please enter a valid amount for {self.user.username}.", messages
        )

    def test_add_expense_pro_amount_split_negative_amount_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "100",
                "payer": str(self.user.id),
                "split_type": "AMOUNT",
                "participants": [str(self.user.id)],
                f"amount_{self.user.id}": "-10",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Split amounts cannot be negative.", messages)

    def test_add_expense_pro_amount_split_wrong_sum_error(self):
        response = self.client.post(
            self.url,
            {
                "title": "X",
                "amount": "100",
                "payer": str(self.user.id),
                "split_type": "AMOUNT",
                "participants": [str(self.user.id)],
                f"amount_{self.user.id}": "90",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Split amounts must add up to $100.00." in m for m in messages)
        )
