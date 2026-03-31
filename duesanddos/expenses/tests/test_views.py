from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from accounts.models import CustomUser, Profile
from households.models import Household, HouseholdMember
from expenses.models import Expense, ExpenseSplit
from activities.models import ActivityLog

TEST_PASSWORD = "TestPass123!"


class ExpenseViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="exuser",
            email="ex@example.com",
            password=TEST_PASSWORD,
        )
        self.user2 = CustomUser.objects.create_user(
            username="exuser2",
            email="ex2@example.com",
            password=TEST_PASSWORD,
        )
        self.hh = Household.objects.create(name="Expense House")
        HouseholdMember.objects.create(user=self.user, household=self.hh, role="Admin")
        HouseholdMember.objects.create(
            user=self.user2, household=self.hh, role="Member"
        )
        self.profile = Profile.objects.create(user=self.user, active_household=self.hh)
        Profile.objects.create(user=self.user2, active_household=self.hh)
        self.client.login(username="exuser", password=TEST_PASSWORD)

    # --- Add Expense Pro ---
    def test_add_expense_pro_success_equal(self):
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {
                "title": "Groceries",
                "amount": "90.00",
                "payer": self.user.id,
                "split_type": "EQUAL",
                "participants": [self.user.id, self.user2.id],
            },
        )
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(title="Groceries")
        self.assertEqual(expense.splits.count(), 2)

    # --- Delete Expense Pro ---
    def test_delete_expense_pro_success(self):
        expense = Expense.objects.create(
            title="To Delete",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.hh,
        )
        url = reverse("delete_expense_pro", args=[expense.id])
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse("expenses_list"))
        self.assertFalse(Expense.objects.filter(id=expense.id).exists())
        self.assertTrue(ActivityLog.objects.filter(action="EXPENSE_DELETED").exists())

    # --- Edit Expense Pro ---
    def test_edit_expense_pro_success(self):
        expense = Expense.objects.create(
            title="Old",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.hh,
        )
        url = reverse("edit_expense_pro", args=[expense.id])
        self.client.post(
            url,
            {
                "title": "New Title",
                "amount": "20.00",
                "split_type": "EQUAL",
                "participants": [self.user.id, self.user2.id],
            },
            follow=True,
        )
        expense.refresh_from_db()
        self.assertEqual(expense.title, "New Title")

    # --- Settle Split ---
    def test_settle_split_success(self):
        expense = Expense.objects.create(
            title="Debt",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.hh,
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=Decimal("10.00")
        )
        url = reverse("settle_split", args=[split.id])
        self.client.login(username="exuser2", password=TEST_PASSWORD)
        self.client.post(url, follow=True)
        split.refresh_from_db()
        self.assertTrue(split.is_settled)

    # --- Expense History ---
    def test_expense_history_view(self):
        url = reverse("expense_history")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # --- Expenses List ---
    def test_expenses_list_view(self):
        url = reverse("expenses_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
