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
        self.profile2 = Profile.objects.create(
            user=self.user2, active_household=self.hh
        )
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
        # Verify Activity Log
        self.assertTrue(ActivityLog.objects.filter(action="EXPENSE_ADDED").exists())

    # --- Settle Split ---
    def test_settle_split_success(self):
        expense = Expense.objects.create(
            title="D", amount=10, payer=self.user, household=self.hh
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=10
        )
        url = reverse("settle_split", args=[split.id])
        # Payee settles
        self.client.login(username="exuser2", password=TEST_PASSWORD)
        response = self.client.post(url, follow=True)
        self.assertContains(response, "settled!")
        split.refresh_from_db()
        self.assertTrue(split.is_settled)

    def test_delete_expense_pro_success(self):
        expense = Expense.objects.create(
            title="To Delete", amount=10, payer=self.user, household=self.hh
        )
        url = reverse("delete_expense_pro", args=[expense.id])
        response = self.client.post(url, follow=True)
        self.assertContains(response, "deleted successfully")
        self.assertFalse(Expense.objects.filter(id=expense.id).exists())

    def test_edit_expense_pro_success_equal(self):
        expense = Expense.objects.create(
            title="Old", amount=10, payer=self.user, household=self.hh
        )
        url = reverse("edit_expense_pro", args=[expense.id])
        response = self.client.post(
            url,
            {
                "title": "New Title",
                "amount": "20.00",
                "split_type": "EQUAL",
                "participants": [self.user.id, self.user2.id],
            },
            follow=True,
        )
        self.assertContains(response, "updated successfully")
        expense.refresh_from_db()
        self.assertEqual(expense.title, "New Title")
        self.assertEqual(expense.splits.count(), 2)

    def test_add_expense_pro_success_percent(self):
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {
                "title": "Percent Split",
                "amount": "100.00",
                "payer": self.user.id,
                "split_type": "PERCENT",
                "participants": [self.user.id, self.user2.id],
                f"percent_{self.user.id}": "60",
                f"percent_{self.user2.id}": "40",
            },
        )
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(title="Percent Split")
        self.assertEqual(
            expense.splits.get(user=self.user).amount_owed, Decimal("60.00")
        )
        self.assertEqual(
            expense.splits.get(user=self.user2).amount_owed, Decimal("40.00")
        )

    def test_add_expense_pro_success_amount(self):
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {
                "title": "Amount Split",
                "amount": "100.00",
                "payer": self.user.id,
                "split_type": "AMOUNT",
                "participants": [self.user.id, self.user2.id],
                f"amount_{self.user.id}": "70.00",
                f"amount_{self.user2.id}": "30.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(title="Amount Split")
        self.assertEqual(
            expense.splits.get(user=self.user).amount_owed, Decimal("70.00")
        )

    def test_add_expense_pro_get_not_allowed(self):
        url = reverse("add_expense_pro")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("expenses_list"))

    def test_add_expense_pro_no_household(self):
        self.profile.active_household = None
        self.profile.save()
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {"title": "T", "amount": "10", "participants": [self.user.id]},
            follow=True,
        )
        self.assertContains(response, "Please select an active household first.")

    def test_add_expense_pro_invalid_data(self):
        url = reverse("add_expense_pro")
        # No title
        response = self.client.post(
            url, {"amount": "10", "participants": [self.user.id]}, follow=True
        )
        self.assertContains(response, "Please enter a title for the expense.")

        # No amount/participants
        response = self.client.post(url, {"title": "T"}, follow=True)
        self.assertContains(
            response, "Please provide an amount and select at least one person."
        )

        # Invalid amount
        response = self.client.post(
            url,
            {"title": "T", "amount": "abc", "participants": [self.user.id]},
            follow=True,
        )
        self.assertContains(response, "Please enter a valid total amount.")

        # Negative amount
        response = self.client.post(
            url,
            {"title": "T", "amount": "-10", "participants": [self.user.id]},
            follow=True,
        )
        self.assertContains(response, "Total amount must be greater than 0.")

    def test_add_expense_pro_invalid_payer(self):
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "10",
                "payer": 9999,
                "participants": [self.user.id],
            },
            follow=True,
        )
        self.assertContains(response, "Selected payer was not found.")

        user3 = CustomUser.objects.create_user(
            username="u3", email="u3@ex.com", password=TEST_PASSWORD
        )
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "10",
                "payer": user3.id,
                "participants": [self.user.id],
            },
            follow=True,
        )
        self.assertContains(
            response, "Selected payer is not part of the active household."
        )

    def test_add_expense_pro_invalid_participants(self):
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "10",
                "payer": self.user.id,
                "participants": [9999],
                "split_type": "EQUAL",
            },
            follow=True,
        )
        self.assertContains(response, "One or more selected participants are invalid.")

    def test_add_expense_pro_invalid_split_type(self):
        url = reverse("add_expense_pro")
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "10",
                "payer": self.user.id,
                "participants": [self.user.id],
                "split_type": "INVALID",
            },
            follow=True,
        )
        self.assertContains(response, "Invalid split type.")

    def test_add_expense_pro_percent_errors(self):
        url = reverse("add_expense_pro")
        # Invalid percent
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "payer": self.user.id,
                "participants": [self.user.id],
                "split_type": "PERCENT",
                f"percent_{self.user.id}": "abc",
            },
            follow=True,
        )
        self.assertContains(
            response, f"Please enter a valid percentage for {self.user.username}."
        )

        # Negative percent
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "payer": self.user.id,
                "participants": [self.user.id],
                "split_type": "PERCENT",
                f"percent_{self.user.id}": "-10",
            },
            follow=True,
        )
        self.assertContains(response, "Percentages cannot be negative.")

        # Total not 100
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "payer": self.user.id,
                "participants": [self.user.id],
                "split_type": "PERCENT",
                f"percent_{self.user.id}": "90",
            },
            follow=True,
        )
        self.assertContains(response, "Percentages must add up to exactly 100.")

    def test_add_expense_pro_amount_errors(self):
        url = reverse("add_expense_pro")
        # Invalid amount
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "payer": self.user.id,
                "participants": [self.user.id],
                "split_type": "AMOUNT",
                f"amount_{self.user.id}": "abc",
            },
            follow=True,
        )
        self.assertContains(
            response, f"Please enter a valid amount for {self.user.username}."
        )

        # Negative amount
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "payer": self.user.id,
                "participants": [self.user.id],
                "split_type": "AMOUNT",
                f"amount_{self.user.id}": "-10",
            },
            follow=True,
        )
        self.assertContains(response, "Split amounts cannot be negative.")

        # Total mismatch
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "payer": self.user.id,
                "participants": [self.user.id],
                "split_type": "AMOUNT",
                f"amount_{self.user.id}": "90",
            },
            follow=True,
        )
        self.assertContains(
            response, "Split amounts must add up to $100.00. Current total is $90.00."
        )

    # --- Settle Split ---
    def test_settle_split_no_household(self):
        expense = Expense.objects.create(
            title="D", amount=10, payer=self.user, household=self.hh
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=10
        )
        self.profile.active_household = None
        self.profile.save()
        url = reverse("settle_split", args=[split.id])
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Please set an active household first.")

    def test_settle_split_not_found(self):
        url = reverse("settle_split", args=[9999])
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Split not found.")

    def test_settle_split_already_settled(self):
        expense = Expense.objects.create(
            title="D", amount=10, payer=self.user, household=self.hh
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=10, is_settled=True
        )
        url = reverse("settle_split", args=[split.id])
        response = self.client.post(url, follow=True)
        self.assertContains(response, "This payment is already settled.")

    def test_settle_split_no_permission(self):
        user3 = CustomUser.objects.create_user(
            username="u3", email="u3@ex.com", password=TEST_PASSWORD
        )
        HouseholdMember.objects.create(user=user3, household=self.hh)
        Profile.objects.create(user=user3, active_household=self.hh)
        expense = Expense.objects.create(
            title="D", amount=10, payer=self.user, household=self.hh
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=10
        )

        self.client.login(username="u3", password=TEST_PASSWORD)
        url = reverse("settle_split", args=[split.id])
        response = self.client.post(url, follow=True)
        self.assertContains(
            response, "You do not have permission to settle this split."
        )

    # --- Delete Expense Pro ---
    def test_delete_expense_pro_fails(self):
        expense = Expense.objects.create(
            title="D", amount=10, payer=self.user2, household=self.hh
        )
        url = reverse("delete_expense_pro", args=[expense.id])

        # Wrong method
        response = self.client.get(url)
        self.assertRedirects(response, reverse("expenses_list"))

        # No household
        self.profile.active_household = None
        self.profile.save()
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Please select an active household first.")

        # Not found
        self.profile.active_household = self.hh
        self.profile.save()
        url_fake = reverse("delete_expense_pro", args=[9999])
        response = self.client.post(url_fake, follow=True)
        self.assertContains(response, "Expense not found.")

        # Not payer
        url = reverse("delete_expense_pro", args=[expense.id])
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Only the payer can delete it.")

    # --- Edit Expense Pro ---
    def test_edit_expense_pro_fails(self):
        expense = Expense.objects.create(
            title="D", amount=10, payer=self.user2, household=self.hh
        )
        url = reverse("edit_expense_pro", args=[expense.id])

        # No household
        self.profile.active_household = None
        self.profile.save()
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Please select an active household first.")

        # Not found
        self.profile.active_household = self.hh
        self.profile.save()
        url_fake = reverse("edit_expense_pro", args=[9999])
        response = self.client.post(url_fake, follow=True)
        self.assertContains(response, "Expense not found.")

        # Not payer
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Only the payer can edit this expense.")

        # GET not allowed
        expense.payer = self.user
        expense.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Missing data
        response = self.client.post(url, {}, follow=True)
        self.assertContains(response, "Title, amount, and participants are required.")

        # Invalid amount
        response = self.client.post(
            url,
            {"title": "T", "amount": "abc", "participants": [self.user.id]},
            follow=True,
        )
        self.assertContains(response, "Invalid amount.")

    def test_edit_expense_pro_split_types(self):
        expense = Expense.objects.create(
            title="D", amount=10, payer=self.user, household=self.hh
        )
        url = reverse("edit_expense_pro", args=[expense.id])

        # PERCENT
        self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "split_type": "PERCENT",
                "participants": [self.user.id, self.user2.id],
                f"percent_{self.user.id}": "50",
                f"percent_{self.user2.id}": "50",
            },
        )
        expense.refresh_from_db()
        self.assertEqual(expense.splits.count(), 2)

        # AMOUNT success
        self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "split_type": "AMOUNT",
                "participants": [self.user.id, self.user2.id],
                f"amount_{self.user.id}": "40.00",
                f"amount_{self.user2.id}": "60.00",
            },
        )
        expense.refresh_from_db()
        self.assertEqual(
            expense.splits.get(user=self.user).amount_owed, Decimal("40.00")
        )

        # AMOUNT errors
        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "split_type": "AMOUNT",
                "participants": [self.user.id],
                f"amount_{self.user.id}": "abc",
            },
            follow=True,
        )
        self.assertContains(
            response, f"Please enter a valid amount for {self.user.username}."
        )

        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "split_type": "AMOUNT",
                "participants": [self.user.id],
                f"amount_{self.user.id}": "-10",
            },
            follow=True,
        )
        self.assertContains(response, "Split amounts cannot be negative.")

        response = self.client.post(
            url,
            {
                "title": "T",
                "amount": "100",
                "split_type": "AMOUNT",
                "participants": [self.user.id],
                f"amount_{self.user.id}": "50",
            },
            follow=True,
        )
        self.assertContains(
            response, "Split amounts must add up to $100.00. Current total is $50.00."
        )

    def test_legacy_add_expense(self):
        url = reverse("add_expense")
        response = self.client.post(
            url, {"title": "Legacy", "amount": "50"}, follow=True
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(Expense.objects.filter(title="Legacy").exists())

    def test_views_no_household(self):
        # Clear active household and memberships to be sure
        Profile.objects.filter(user=self.user).update(active_household=None)
        HouseholdMember.objects.filter(user=self.user).delete()

        # expenses_list_view
        response = self.client.get(reverse("expenses_list"))
        self.assertRedirects(response, reverse("household_settings"))

        # expense_history_view
        response = self.client.get(reverse("expense_history"))
        self.assertRedirects(response, reverse("household_settings"))

    def test_expenses_list_view_success(self):
        url = reverse("expenses_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_expense_history_view_success(self):
        url = reverse("expense_history")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
