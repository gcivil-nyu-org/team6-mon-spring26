from datetime import date, datetime
import json
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser, Profile
from chores.models import Chore, ChoreCompletion, ChoreSkip
from expenses.models import Expense
from households.models import Household, HouseholdMember
from insights.views import _add_months, _day_label, _month_starts, _subtract_one_month


TEST_PASSWORD = "TestPass123!"


class InsightsHelpersTests(TestCase):
    def test_add_months_same_year(self):
        self.assertEqual(_add_months(date(2026, 4, 1), 1), date(2026, 5, 1))

    def test_add_months_rolls_over_year(self):
        self.assertEqual(_add_months(date(2026, 11, 1), 3), date(2027, 2, 1))

    def test_month_starts_returns_inclusive_range(self):
        self.assertEqual(
            _month_starts(date(2026, 3, 1), date(2026, 5, 1)),
            [date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)],
        )

    def test_day_label(self):
        self.assertEqual(_day_label(date(2026, 4, 11)), "Apr 11")


class InsightsViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="insightsuser",
            email="insights@example.com",
            password=TEST_PASSWORD,
        )
        self.other_user = CustomUser.objects.create_user(
            username="roommate",
            email="roommate@example.com",
            password=TEST_PASSWORD,
        )

        self.household = Household.objects.create(name="Insights House")
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        HouseholdMember.objects.create(
            user=self.other_user, household=self.household, role="Member"
        )

        self.profile, _ = Profile.objects.update_or_create(
            user=self.user, defaults={"active_household": self.household}
        )
        self.other_profile, _ = Profile.objects.update_or_create(
            user=self.other_user, defaults={"active_household": self.household}
        )

        self.url = reverse("insights")

    def login(self):
        self.client.login(username="insightsuser", password=TEST_PASSWORD)

    def create_expense(self, title, amount, payer, spent_on):
        return Expense.objects.create(
            title=title,
            amount=amount,
            payer=payer,
            household=self.household,
            date_spent=spent_on,
        )

    def create_daily_chore(
        self, description="Daily chore", created_by=None, **overrides
    ):
        payload = {
            "household": self.household,
            "description": description,
            "repeat_type": "DAILY",
            "start_date": date(2026, 4, 1),
            "created_by": created_by or self.user,
            "is_active": True,
        }
        payload.update(overrides)
        return Chore.objects.create(**payload)

    def create_completion(
        self,
        chore,
        occurrence_date,
        completed_by,
        completed_at,
    ):
        completion = ChoreCompletion.objects.create(
            chore=chore,
            occurrence_date=occurrence_date,
            completed_by=completed_by,
        )
        ChoreCompletion.objects.filter(pk=completion.pk).update(
            completed_at=timezone.make_aware(completed_at)
        )
        completion.refresh_from_db()
        return completion

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_no_household_renders_empty_state(self):
        self.profile.active_household = None
        self.profile.save(update_fields=["active_household"])

        self.login()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["no_household"])

    @patch("insights.views.render")
    @patch("insights.views.Profile.objects.get_or_create")
    def test_household_descriptor_exception_is_handled(
        self,
        mock_get_or_create,
        mock_render,
    ):
        self.login()

        class BrokenProfile:
            def __init__(self):
                self._active_household = None
                self.saved_update_fields = None

            @property
            def active_household(self):
                raise Household.DoesNotExist()

            @active_household.setter
            def active_household(self, value):
                self._active_household = value

            def save(self, update_fields=None):
                self.saved_update_fields = update_fields

        broken_profile = BrokenProfile()
        mock_get_or_create.return_value = (broken_profile, False)
        mock_render.return_value = HttpResponse("ok")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(broken_profile._active_household, None)
        self.assertEqual(broken_profile.saved_update_fields, ["active_household"])
        mock_render.assert_called_once_with(
            response.wsgi_request,
            "insights/index.html",
            {"no_household": True},
        )

    @patch("insights.views.timezone.localdate", return_value=date(2026, 4, 11))
    def test_invalid_dates_fall_back_to_default_month_window(self, _mock_localdate):
        self.login()

        response = self.client.get(
            self.url,
            {
                "start_date": "not-a-date",
                "end_date": "still-not-a-date",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["end_date"], date(2026, 4, 11))
        self.assertEqual(response.context["start_date"], date(2026, 3, 11))

    def test_subtract_one_month_same_day(self):
        self.assertEqual(_subtract_one_month(date(2026, 4, 11)), date(2026, 3, 11))

    def test_subtract_one_month_handles_shorter_previous_month(self):
        self.assertEqual(_subtract_one_month(date(2026, 3, 31)), date(2026, 2, 28))

    def test_subtract_one_month_handles_january(self):
        self.assertEqual(_subtract_one_month(date(2026, 1, 15)), date(2025, 12, 15))

    def test_reversed_dates_are_swapped(self):
        self.create_expense("March expense", "5.00", self.user, date(2026, 3, 30))
        self.create_expense("April expense", "7.00", self.user, date(2026, 4, 2))

        self.login()
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-04-03",
                "end_date": "2026-03-30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["start_date"], date(2026, 3, 30))
        self.assertEqual(response.context["end_date"], date(2026, 4, 3))

        self.assertEqual(
            json.loads(response.context["monthly_labels_json"]),
            ["Mar 2026", "Apr 2026"],
        )
        self.assertEqual(
            json.loads(response.context["monthly_expenses_json"]),
            [5.0, 7.0],
        )

    def test_empty_household_data_returns_zeroed_insights(self):
        self.login()
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-04-01",
                "end_date": "2026-04-03",
            },
        )

        self.assertEqual(response.status_code, 200)

        cards = response.context["insights_cards"]
        self.assertEqual(cards["total_spent"], 0.0)
        self.assertEqual(cards["average_expense"], 0)
        self.assertEqual(cards["previous_total"], 0.0)
        self.assertEqual(cards["spending_change"], 0.0)
        self.assertEqual(cards["completed_chores"], 0)
        self.assertEqual(cards["due_chores"], 0)

        self.assertEqual(json.loads(response.context["monthly_expenses_json"]), [0.0])
        self.assertEqual(
            json.loads(response.context["daily_labels_json"]),
            ["Apr 1", "Apr 2", "Apr 3"],
        )
        self.assertEqual(
            json.loads(response.context["daily_values_json"]),
            [0.0, 0.0, 0.0],
        )
        self.assertEqual(
            json.loads(response.context["chore_status_values_json"]),
            [0, 0, 0],
        )
        self.assertEqual(
            json.loads(response.context["completion_member_labels_json"]),
            [],
        )
        self.assertEqual(
            json.loads(response.context["completion_member_values_json"]),
            [],
        )
        self.assertEqual(response.context["top_spenders"], [])

    def test_view_builds_expected_expense_and_chore_context(self):
        self.create_expense("Groceries", "10.00", self.user, date(2026, 4, 1))
        self.create_expense("Utilities", "20.00", self.other_user, date(2026, 4, 2))
        self.create_expense(
            "Previous period bill", "15.00", self.user, date(2026, 3, 30)
        )

        due_chore = self.create_daily_chore(description="Due chore")
        overdue_chore = self.create_daily_chore(
            description="Overdue chore",
            start_date=date(2026, 3, 28),
        )

        self.create_completion(
            chore=due_chore,
            occurrence_date=date(2026, 4, 1),
            completed_by=self.user,
            completed_at=datetime(2026, 4, 1, 9, 0, 0),
        )
        ChoreSkip.objects.create(
            chore=due_chore,
            occurrence_date=date(2026, 4, 2),
            skipped_by=self.other_user,
        )

        self.create_completion(
            chore=overdue_chore,
            occurrence_date=date(2026, 3, 31),
            completed_by=self.other_user,
            completed_at=datetime(2026, 4, 2, 10, 30, 0),
        )

        self.login()
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-04-01",
                "end_date": "2026-04-03",
            },
        )

        self.assertEqual(response.status_code, 200)

        cards = response.context["insights_cards"]
        self.assertEqual(cards["total_spent"], 30.0)
        self.assertEqual(cards["average_expense"], 15.0)
        self.assertEqual(cards["previous_total"], 15.0)
        self.assertEqual(cards["spending_change"], 100.0)
        self.assertEqual(cards["completed_chores"], 2)
        self.assertEqual(cards["due_chores"], 6)

        self.assertEqual(
            json.loads(response.context["monthly_labels_json"]),
            ["Apr 2026"],
        )
        self.assertEqual(
            json.loads(response.context["monthly_expenses_json"]),
            [30.0],
        )

        self.assertEqual(
            json.loads(response.context["member_labels_json"]),
            ["roommate", "insightsuser"],
        )
        self.assertEqual(
            json.loads(response.context["member_totals_json"]),
            [20.0, 10.0],
        )

        self.assertEqual(
            json.loads(response.context["daily_labels_json"]),
            ["Apr 1", "Apr 2", "Apr 3"],
        )
        self.assertEqual(
            json.loads(response.context["daily_values_json"]),
            [10.0, 20.0, 0.0],
        )

        self.assertEqual(response.context["chore_window_start"], date(2026, 4, 1))
        self.assertEqual(
            json.loads(response.context["chore_status_labels_json"]),
            ["Completed on time/in-window", "Skipped", "Still open"],
        )
        self.assertEqual(
            json.loads(response.context["chore_status_values_json"]),
            [1, 1, 4],
        )

        self.assertEqual(
            json.loads(response.context["completion_member_labels_json"]),
            ["insightsuser", "roommate"],
        )
        self.assertEqual(
            json.loads(response.context["completion_member_values_json"]),
            [1, 1],
        )

        top_spenders = response.context["top_spenders"]
        self.assertEqual(len(top_spenders), 2)
        self.assertEqual(top_spenders[0]["payer__username"], "roommate")
        self.assertEqual(float(top_spenders[0]["total"]), 20.0)
        self.assertEqual(top_spenders[0]["expense_count"], 1)
        self.assertEqual(top_spenders[1]["payer__username"], "insightsuser")
        self.assertEqual(float(top_spenders[1]["total"]), 10.0)
        self.assertEqual(top_spenders[1]["expense_count"], 1)

    def test_inactive_and_out_of_range_chores_do_not_count(self):
        active_daily = self.create_daily_chore(description="Active daily")
        inactive_daily = self.create_daily_chore(
            description="Inactive daily",
            is_active=False,
        )
        future_daily = self.create_daily_chore(
            description="Future daily",
            start_date=date(2026, 4, 5),
        )

        self.create_completion(
            chore=active_daily,
            occurrence_date=date(2026, 4, 1),
            completed_by=self.user,
            completed_at=datetime(2026, 4, 1, 8, 0, 0),
        )

        self.create_completion(
            chore=inactive_daily,
            occurrence_date=date(2026, 4, 1),
            completed_by=self.user,
            completed_at=datetime(2026, 4, 1, 9, 0, 0),
        )

        self.create_completion(
            chore=future_daily,
            occurrence_date=date(2026, 4, 5),
            completed_by=self.user,
            completed_at=datetime(2026, 4, 5, 10, 0, 0),
        )

        self.login()
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-04-01",
                "end_date": "2026-04-03",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.context["chore_status_values_json"]),
            [2, 0, 1],
        )
        self.assertEqual(response.context["insights_cards"]["completed_chores"], 2)
        self.assertEqual(response.context["insights_cards"]["due_chores"], 3)
        self.assertEqual(
            json.loads(response.context["completion_member_labels_json"]),
            ["insightsuser"],
        )
        self.assertEqual(
            json.loads(response.context["completion_member_values_json"]),
            [2],
        )

    def test_overdue_completion_in_range_counts_without_affecting_due_status(self):
        chore = self.create_daily_chore(
            description="Overdue completion chore",
            start_date=date(2026, 3, 28),
        )

        self.create_completion(
            chore=chore,
            occurrence_date=date(2026, 3, 31),
            completed_by=self.user,
            completed_at=datetime(2026, 4, 2, 14, 0, 0),
        )

        self.login()
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-04-01",
                "end_date": "2026-04-03",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["insights_cards"]["completed_chores"], 1)
        self.assertEqual(response.context["insights_cards"]["due_chores"], 3)
        self.assertEqual(
            json.loads(response.context["chore_status_values_json"]),
            [0, 0, 3],
        )
        self.assertEqual(
            json.loads(response.context["completion_member_labels_json"]),
            ["insightsuser"],
        )
        self.assertEqual(
            json.loads(response.context["completion_member_values_json"]),
            [1],
        )
