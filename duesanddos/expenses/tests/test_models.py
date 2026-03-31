from django.test import TestCase
from accounts.models import CustomUser
from households.models import Household, HouseholdMember
from expenses.models import Expense, ExpenseSplit

TEST_PASSWORD = "TestPass123!"


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="payer",
            email="payer@example.com",
            password=TEST_PASSWORD,
        )
        self.hh = Household.objects.create(name="Expense House")
        HouseholdMember.objects.create(user=self.user, household=self.hh, role="Admin")

    def test_expense_str_returns_title_and_amount(self):
        expense = Expense.objects.create(
            title="Groceries",
            amount="42.50",
            payer=self.user,
            household=self.hh,
            split_type="EQUAL",
        )
        self.assertEqual(str(expense), "Groceries ($42.50)")

    def test_expense_default_split_type_is_equal(self):
        expense = Expense.objects.create(
            title="Utilities",
            amount="90.00",
            payer=self.user,
            household=self.hh,
        )
        self.assertEqual(expense.split_type, "EQUAL")

    def test_expense_accepts_amount_split_type(self):
        expense = Expense.objects.create(
            title="Dinner",
            amount="75.00",
            payer=self.user,
            household=self.hh,
            split_type="AMOUNT",
        )
        self.assertEqual(expense.split_type, "AMOUNT")


class ExpenseSplitModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="splituser",
            email="split@example.com",
            password=TEST_PASSWORD,
        )
        self.user2 = CustomUser.objects.create_user(
            username="splituser2",
            email="split2@example.com",
            password=TEST_PASSWORD,
        )
        self.hh = Household.objects.create(name="Split House")
        HouseholdMember.objects.create(user=self.user, household=self.hh, role="Admin")
        HouseholdMember.objects.create(
            user=self.user2, household=self.hh, role="Member"
        )
        self.expense = Expense.objects.create(
            title="Internet",
            amount="60.00",
            payer=self.user,
            household=self.hh,
            split_type="EQUAL",
        )

    def test_expense_split_str_returns_expected_text(self):
        split = ExpenseSplit.objects.create(
            expense=self.expense,
            user=self.user,
            amount_owed="60.00",
        )
        self.assertEqual(
            str(split),
            "splituser owes $60.00 for Internet",
        )

    def test_expense_split_count_for_created_expense(self):
        expense = Expense.objects.create(
            title="Test Expense",
            amount="30.00",
            payer=self.user,
            household=self.hh,
            split_type="AMOUNT",
        )
        ExpenseSplit.objects.create(
            expense=expense, user=self.user, amount_owed="10.00"
        )
        ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed="20.00"
        )

        self.assertEqual(expense.splits.count(), 2)
