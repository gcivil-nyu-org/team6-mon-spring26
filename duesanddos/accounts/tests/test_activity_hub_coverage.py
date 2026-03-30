from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import (
    Profile,
    Household,
    HouseholdMember,
    Expense,
    ExpenseSplit,
    ActivityLog,
)

User = get_user_model()
TEST_PASSWORD = "TestPass123!"


class ActivityHubCoverageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payeruser", email="payer@example.com", password=TEST_PASSWORD
        )
        self.user2 = User.objects.create_user(
            username="roommate1", email="room1@example.com", password=TEST_PASSWORD
        )
        self.household = Household.objects.create(name="Test House")

        self.profile = Profile.objects.create(
            user=self.user, active_household=self.household
        )
        self.profile2 = Profile.objects.create(
            user=self.user2, active_household=self.household
        )

        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        HouseholdMember.objects.create(
            user=self.user2, household=self.household, role="Member"
        )

        self.client.login(username="payeruser", password=TEST_PASSWORD)

    # --- Activity Log View Tests ---

    def test_activity_log_view_success(self):
        url = reverse("activity_log")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/activity.html")

    def test_activity_log_view_redirect_if_no_household(self):
        self.profile.active_household = None
        self.profile.save()
        url = reverse("activity_log")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("household_settings"))

    def test_activity_log_filtering(self):
        ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="EXPENSE_ADDED",
            details="Added X",
        )
        ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="PAYMENT_SETTLED",
            details="Settled Y",
        )

        url = reverse("activity_log")
        # Filter action
        response = self.client.get(url, {"action": "EXPENSE_ADDED"})
        self.assertEqual(len(response.context["activities"]), 1)
        self.assertEqual(response.context["activities"][0].action, "EXPENSE_ADDED")

        # Filter date range (happy path)
        today = timezone.now().date()
        start = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        response = self.client.get(url, {"start_date": start, "end_date": end})
        self.assertEqual(response.status_code, 200)

        # Invalid date fallback
        response = self.client.get(
            url, {"start_date": "invalid-date", "end_date": "2026-99-99"}
        )
        self.assertEqual(response.status_code, 200)
        # Should default to start of month to today
        self.assertEqual(
            response.context["start_date"], timezone.now().date().replace(day=1)
        )

    # --- Delete Expense Pro View Tests ---

    def test_delete_expense_pro_success(self):
        expense = Expense.objects.create(
            title="To Delete",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("delete_expense_pro", args=[expense.id])

        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse("expenses_list"))
        self.assertFalse(Expense.objects.filter(id=expense.id).exists())

        # Verify Activity Log
        self.assertTrue(
            ActivityLog.objects.filter(
                action="EXPENSE_DELETED", details__contains="To Delete"
            ).exists()
        )

    def test_delete_expense_pro_unauthorized(self):
        # User2 (roommate) trying to delete User's expense
        expense = Expense.objects.create(
            title="Payer's Expense",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("delete_expense_pro", args=[expense.id])

        self.client.login(username="roommate1", password=TEST_PASSWORD)
        response = self.client.post(url, follow=True)
        self.assertTrue(Expense.objects.filter(id=expense.id).exists())
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("permission to delete", messages[0].lower())

    def test_delete_expense_pro_not_found(self):
        url = reverse("delete_expense_pro", args=[99999])
        response = self.client.post(url, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("not found", messages[0].lower())

    def test_delete_expense_pro_not_post(self):
        expense = Expense.objects.create(
            title="GET Delete",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("delete_expense_pro", args=[expense.id])
        response = self.client.get(url, follow=True)
        # Should redirect quietly, not delete
        self.assertTrue(Expense.objects.filter(id=expense.id).exists())
        self.assertRedirects(response, reverse("expenses_list"))

    def test_delete_expense_pro_no_household(self):
        expense = Expense.objects.create(
            title="Orphan Delete",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        self.profile.active_household = None
        self.profile.save()
        url = reverse("delete_expense_pro", args=[expense.id])
        response = self.client.post(url, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("active household", messages[0].lower())

    # --- Edit Expense Pro View Tests ---

    def test_edit_expense_pro_success_equal(self):
        expense = Expense.objects.create(
            title="Old Title",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
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
        self.assertEqual(expense.amount, Decimal("20.00"))
        self.assertEqual(expense.splits.count(), 2)

    def test_edit_expense_pro_amount_split_valid(self):
        expense = Expense.objects.create(
            title="Lunch",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])

        self.client.post(
            url,
            {
                "title": "Lunch Edited",
                "amount": "15.00",
                "split_type": "AMOUNT",
                "participants": [self.user.id, self.user2.id],
                f"amount_{self.user.id}": "10.00",
                f"amount_{self.user2.id}": "5.00",
            },
            follow=True,
        )

        self.assertEqual(
            expense.splits.get(user=self.user2).amount_owed, Decimal("5.00")
        )

    def test_edit_expense_pro_amount_split_invalid_sum(self):
        expense = Expense.objects.create(
            title="Lunch",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])

        response = self.client.post(
            url,
            {
                "title": "Lunch Edited",
                "amount": "15.00",
                "split_type": "AMOUNT",
                "participants": [self.user.id, self.user2.id],
                f"amount_{self.user.id}": "10.00",
                f"amount_{self.user2.id}": "10.00",  # Total 20 != 15
            },
            follow=True,
        )

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("add up" in m.lower() for m in messages))

    def test_edit_expense_pro_percent_split(self):
        expense = Expense.objects.create(
            title="Bill",
            amount=Decimal("100.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])

        self.client.post(
            url,
            {
                "title": "Bill Edited",
                "amount": "100.00",
                "split_type": "PERCENT",
                "participants": [self.user.id, self.user2.id],
                f"percent_{self.user.id}": "70",
                f"percent_{self.user2.id}": "30",
            },
            follow=True,
        )

        self.assertEqual(
            expense.splits.get(user=self.user2).amount_owed, Decimal("30.00")
        )

    def test_edit_expense_pro_no_household(self):
        expense = Expense.objects.create(
            title="Edit Orphan",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        self.profile.active_household = None
        self.profile.save()
        url = reverse("edit_expense_pro", args=[expense.id])
        response = self.client.post(url, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("active household", messages[0].lower())

    def test_edit_expense_pro_not_post(self):
        expense = Expense.objects.create(
            title="GET Edit",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])
        self.client.get(url, follow=True)
        self.assertEqual(expense.title, "GET Edit")

    def test_edit_expense_pro_missing_fields(self):
        expense = Expense.objects.create(
            title="Missing Edit",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])
        response = self.client.post(url, {"title": ""}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("required" in m.lower() for m in messages))

    def test_edit_expense_pro_invalid_amount_raw(self):
        expense = Expense.objects.create(
            title="Bad Amt",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])
        response = self.client.post(
            url,
            {
                "title": "Bad Amt Edited",
                "amount": "abc",
                "split_type": "EQUAL",
                "participants": [self.user.id],
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("invalid amount" in m.lower() for m in messages))

    def test_edit_expense_pro_amount_split_invalid_split_value(self):
        expense = Expense.objects.create(
            title="Lunch",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])
        response = self.client.post(
            url,
            {
                "title": "Lunch Edited",
                "amount": "15.00",
                "split_type": "AMOUNT",
                "participants": [self.user.id, self.user2.id],
                f"amount_{self.user.id}": "abc",
                f"amount_{self.user2.id}": "15.00",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("valid amount" in m.lower() for m in messages))

    def test_edit_expense_pro_amount_split_negative_amount(self):
        expense = Expense.objects.create(
            title="Lunch",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        url = reverse("edit_expense_pro", args=[expense.id])
        response = self.client.post(
            url,
            {
                "title": "Lunch Edited",
                "amount": "15.00",
                "split_type": "AMOUNT",
                "participants": [self.user.id, self.user2.id],
                f"amount_{self.user.id}": "-5.00",
                f"amount_{self.user2.id}": "20.00",
            },
            follow=True,
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("negative" in m.lower() for m in messages))

    # --- Settle Split View Tests ---

    def test_settle_split_success_by_payee(self):
        expense = Expense.objects.create(
            title="Debt",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=Decimal("10.00")
        )
        url = reverse("settle_split", args=[split.id])

        # User2 is the one who owes money (payee of the settlement)
        self.client.login(username="roommate1", password=TEST_PASSWORD)
        self.client.post(url, follow=True)

        split.refresh_from_db()
        self.assertTrue(split.is_settled)
        self.assertEqual(split.settled_by, self.user2)

    def test_settle_split_already_settled(self):
        expense = Expense.objects.create(
            title="Paid",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        split = ExpenseSplit.objects.create(
            expense=expense,
            user=self.user2,
            amount_owed=Decimal("10.00"),
            is_settled=True,
        )
        url = reverse("settle_split", args=[split.id])

        response = self.client.post(url, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("already settled", messages[0].lower())

    def test_settle_split_no_household(self):
        expense = Expense.objects.create(
            title="Not Home",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=Decimal("10.00")
        )
        self.profile.active_household = None
        self.profile.save()
        url = reverse("settle_split", args=[split.id])
        response = self.client.post(url, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("active household" in m.lower() for m in messages))

    def test_settle_split_not_found(self):
        url = reverse("settle_split", args=[99999])
        response = self.client.post(url, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("not found" in m.lower() for m in messages))

    def test_settle_split_unauthorized(self):
        # A 3rd user trying to settle User 2's debt to User 1
        user3 = User.objects.create_user(username="stranger", password=TEST_PASSWORD)
        Profile.objects.create(user=user3, active_household=self.household)
        HouseholdMember.objects.create(
            user=user3, household=self.household, role="Member"
        )

        expense = Expense.objects.create(
            title="Debt",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
        )
        split = ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed=Decimal("10.00")
        )
        url = reverse("settle_split", args=[split.id])

        self.client.login(username="stranger", password=TEST_PASSWORD)
        response = self.client.post(url, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("permission" in m.lower() for m in messages))

    # --- Dashboard View Date Filtering ---

    def test_dashboard_date_filtering(self):
        # Expense yesterday
        yesterday = timezone.now().date() - timedelta(days=1)
        e1 = Expense.objects.create(
            title="Yesterday",
            amount=Decimal("10.00"),
            payer=self.user,
            household=self.household,
            date_spent=yesterday,
        )
        ExpenseSplit.objects.create(
            expense=e1, user=self.user2, amount_owed=Decimal("5.00")
        )

        # Expense last month
        last_month = timezone.now().date() - timedelta(days=35)
        e2 = Expense.objects.create(
            title="Past",
            amount=Decimal("100.00"),
            payer=self.user,
            household=self.household,
            date_spent=last_month,
        )
        ExpenseSplit.objects.create(
            expense=e2, user=self.user2, amount_owed=Decimal("50.00")
        )

        url = reverse("dashboard")

        # Filter only yesterday's range
        start = (yesterday - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (yesterday + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.client.get(url, {"start_date": start, "end_date": end})

        self.assertEqual(response.context["total_spent"], Decimal("10.00"))
        self.assertEqual(response.context["you_are_owed"], 5.0)
