import datetime
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser as User
from accounts.models import Profile
from households.models import Household, HouseholdMember
from chores.models import Chore
from expenses.models import Expense


class NewLogicTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="password", email="test@example.com"
        )
        self.client.login(username="testuser", password="password")
        self.household = Household.objects.create(name="Test Household")
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.profile.active_household = self.household
        self.profile.theme = "dark"
        self.profile.default_calendar_view = "timeGridWeek"
        self.profile.save()

    def test_profile_save_partial_update(self):
        """Test saving profile doesn't overwrite theme/calendar_view."""
        url = reverse("profile")
        # Submit form with ONLY bio, NO theme or default_calendar_view
        response = self.client.post(
            url,
            {
                "save_profile": "1",
                "username": "testuser",
                "first_name": "NewFirst",
                "last_name": "NewLast",
                "email": "test@example.com",
                "bio": "New Bio",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "New Bio")
        # Should NOT be reset to light/dayGridMonth
        self.assertEqual(self.profile.theme, "dark")
        self.assertEqual(self.profile.default_calendar_view, "timeGridWeek")

    def test_add_expense_with_custom_date(self):
        """Test adding expense with a specific payment date."""
        url = reverse("add_expense_pro")
        custom_date = "2023-12-25"
        response = self.client.post(
            url,
            {
                "title": "Christmas Dinner",
                "amount": "100.00",
                "payer": self.user.id,
                "split_type": "EQUAL",
                "date_spent": custom_date,
                "participants": [self.user.id],
            },
        )
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(title="Christmas Dinner")
        self.assertEqual(expense.date_spent.strftime("%Y-%m-%d"), custom_date)

    def test_add_expense_with_invalid_date(self):
        """Test adding expense with an invalid date defaults to today."""
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {
                "title": "Invalid Date Expense",
                "amount": "50.00",
                "payer": self.user.id,
                "split_type": "EQUAL",
                "date_spent": "not-a-date",
                "participants": [self.user.id],
            },
        )
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(title="Invalid Date Expense")
        self.assertEqual(expense.date_spent, datetime.date.today())

    def test_sync_chores_to_gcal_view(self):
        """Test the manual sync GCal view."""
        # Create a chore to sync
        Chore.objects.create(
            description="Sync Me",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
        )
        url = reverse("sync_chores_to_gcal")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("chores_list"))
        # We don't verify the GCal side here as it's mocked in signals,
        # but we verify the view executes and redirects.

    def test_sync_chores_to_gcal_no_household(self):
        """Test sync view fails gracefully if no active household."""
        self.profile.active_household = None
        self.profile.save()
        url = reverse("sync_chores_to_gcal")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("household_settings"))
