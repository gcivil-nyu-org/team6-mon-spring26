from datetime import date, time, timedelta

from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from accounts.models import CustomUser, Profile
from activities.models import ActivityLog
from households.models import Household, HouseholdMember
from .admin import ChoreAdmin
from .apps import ChoresConfig
from .forms import ChoreForm
from .models import Chore, ChoreCompletion, ChoreSkip
from .views import daterange, get_occurrences_for_range

TEST_PASSWORD = "TestPass123!"


class ChoresBaseTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="choreuser",
            email="chore@example.com",
            password=TEST_PASSWORD,
        )
        self.other_user = CustomUser.objects.create_user(
            username="roommate",
            email="roommate@example.com",
            password=TEST_PASSWORD,
        )
        self.household = Household.objects.create(name="Chore House")
        self.profile = Profile.objects.create(
            user=self.user, active_household=self.household
        )
        self.other_profile = Profile.objects.create(
            user=self.other_user, active_household=self.household
        )

        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        HouseholdMember.objects.create(
            user=self.other_user, household=self.household, role="Member"
        )

        self.client.login(username="choreuser", password=TEST_PASSWORD)

    def create_chore(self, **overrides):
        payload = {
            "household": self.household,
            "description": "Take trash out",
            "repeat_type": "ONE_TIME",
            "has_due_date": True,
            "due_date": date.today(),
            "created_by": self.user,
        }
        payload.update(overrides)
        assignees = payload.pop("assignees", None)
        chore = Chore.objects.create(**payload)
        if assignees:
            chore.assignees.set(assignees)
        return chore

    def test_create_chore_helper_sets_assignees(self):
        chore = self.create_chore(
            description="Assigned helper chore",
            assignees=[self.user, self.other_user],
        )

        self.assertEqual(
            set(chore.assignees.all()),
            {self.user, self.other_user},
        )


class ChoreAdminAndConfigTests(TestCase):
    def test_app_config_values(self):
        self.assertEqual(ChoresConfig.name, "chores")
        self.assertEqual(
            ChoresConfig.default_auto_field, "django.db.models.BigAutoField"
        )

    def test_chore_registered_in_admin(self):
        self.assertIn(Chore, site._registry)
        self.assertIsInstance(site._registry[Chore], ChoreAdmin)

    def test_urls_reverse(self):
        self.assertEqual(reverse("chores_list"), "/accounts/chores/")
        self.assertEqual(reverse("add_chore"), "/accounts/chores/add/")
        self.assertEqual(reverse("edit_chore", args=[1]), "/accounts/chores/1/edit/")
        self.assertEqual(
            reverse("delete_chore", args=[1]), "/accounts/chores/1/delete/"
        )
        self.assertEqual(
            reverse("complete_chore_occurrence", args=[1]),
            "/accounts/chores/1/complete/",
        )


class ChoreModelTests(ChoresBaseTestCase):
    def test_model_string_methods(self):
        chore = self.create_chore(description="Mop floor")
        completion = ChoreCompletion.objects.create(
            chore=chore,
            occurrence_date=date.today(),
            completed_by=self.user,
        )
        skip = ChoreSkip.objects.create(
            chore=chore,
            occurrence_date=date.today() + timedelta(days=1),
            skipped_by=self.user,
        )

        self.assertEqual(str(chore), "Mop floor")
        self.assertIn("completed on", str(completion))
        self.assertIn("skipped on", str(skip))

    def test_clean_raises_for_missing_one_time_due_date(self):
        chore = Chore(
            household=self.household,
            description="Laundry",
            repeat_type="ONE_TIME",
            has_due_date=True,
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            chore.clean()

    def test_clean_raises_for_recurring_missing_start_date(self):
        chore = Chore(
            household=self.household,
            description="Dishes",
            repeat_type="DAILY",
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            chore.clean()

    def test_clean_raises_for_weekly_without_selected_day(self):
        chore = Chore(
            household=self.household,
            description="Sweep",
            repeat_type="WEEKLY",
            start_date=date.today(),
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            chore.clean()

    def test_clean_raises_for_end_before_start(self):
        chore = Chore(
            household=self.household,
            description="Vacuum",
            repeat_type="DAILY",
            start_date=date.today(),
            end_date=date.today() - timedelta(days=1),
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            chore.clean()

    def test_weekly_days_property_and_occurs_on(self):
        monday = date(2026, 4, 6)
        tuesday = date(2026, 4, 7)
        chore = Chore(
            household=self.household,
            description="Bins",
            repeat_type="WEEKLY",
            start_date=monday,
            repeat_monday=True,
            created_by=self.user,
        )

        self.assertTrue(chore.weekly_days[0])
        self.assertTrue(chore.occurs_on(monday))
        self.assertFalse(chore.occurs_on(tuesday))

    def test_occurs_on_false_when_inactive(self):
        chore = self.create_chore(is_active=False)
        self.assertFalse(chore.occurs_on(date.today()))

    def test_occurs_on_one_time_without_due_date_false(self):
        chore = self.create_chore(has_due_date=False, due_date=None)
        self.assertFalse(chore.occurs_on(date.today()))

    def test_occurs_on_one_time_matches_due_date(self):
        today = date.today()
        chore = self.create_chore(due_date=today)

        self.assertTrue(chore.occurs_on(today))
        self.assertFalse(chore.occurs_on(today + timedelta(days=1)))

    def test_occurs_on_recurring_without_start_date_false(self):
        chore = Chore(
            household=self.household,
            description="No start",
            repeat_type="DAILY",
            created_by=self.user,
        )
        self.assertFalse(chore.occurs_on(date.today()))

    def test_occurs_on_daily_before_start_and_after_end(self):
        today = date.today()
        chore = Chore(
            household=self.household,
            description="Daily",
            repeat_type="DAILY",
            start_date=today,
            end_date=today + timedelta(days=1),
            created_by=self.user,
        )

        self.assertFalse(chore.occurs_on(today - timedelta(days=1)))
        self.assertTrue(chore.occurs_on(today))
        self.assertFalse(chore.occurs_on(today + timedelta(days=2)))

    def test_occurs_on_unknown_repeat_type_false(self):
        chore = Chore(
            household=self.household,
            description="Odd",
            repeat_type="MONTHLY",
            start_date=date.today(),
            created_by=self.user,
        )
        self.assertFalse(chore.occurs_on(date.today()))


class ChoreFormTests(ChoresBaseTestCase):
    def test_init_optional_fields_and_household_queryset(self):
        form = ChoreForm(household=self.household)

        self.assertFalse(form.fields["due_date"].required)
        self.assertFalse(form.fields["due_time"].required)
        self.assertFalse(form.fields["start_date"].required)
        self.assertFalse(form.fields["end_date"].required)
        self.assertEqual(
            list(form.fields["assignees"].queryset.order_by("id")),
            [self.user, self.other_user],
        )

    def test_init_without_household_leaves_empty_queryset(self):
        form = ChoreForm()
        self.assertEqual(form.fields["assignees"].queryset.count(), 0)

    def test_valid_one_time_form(self):
        form = ChoreForm(
            {
                "description": "Water plants",
                "repeat_type": "ONE_TIME",
                "has_due_date": "on",
                "due_date": date.today().isoformat(),
            },
            household=self.household,
        )
        self.assertTrue(form.is_valid())

    def test_form_requires_due_date_for_one_time_when_checked(self):
        form = ChoreForm(
            {
                "description": "Water plants",
                "repeat_type": "ONE_TIME",
                "has_due_date": "on",
            },
            household=self.household,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("due_date", form.errors)

    def test_form_requires_start_date_for_recurring(self):
        form = ChoreForm(
            {
                "description": "Sweep",
                "repeat_type": "DAILY",
            },
            household=self.household,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)

    def test_form_requires_weekday_for_weekly(self):
        form = ChoreForm(
            {
                "description": "Sweep",
                "repeat_type": "WEEKLY",
                "start_date": date.today().isoformat(),
            },
            household=self.household,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_form_rejects_end_date_before_start_date(self):
        form = ChoreForm(
            {
                "description": "Sweep",
                "repeat_type": "DAILY",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() - timedelta(days=1)).isoformat(),
            },
            household=self.household,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("end_date", form.errors)


class ChoreUtilityFunctionTests(ChoresBaseTestCase):
    def test_daterange_includes_both_endpoints(self):
        start = date.today()
        end = start + timedelta(days=2)
        self.assertEqual(
            list(daterange(start, end)),
            [start, start + timedelta(days=1), end],
        )

    def test_get_occurrences_for_range_respects_completion_and_skip(self):
        start = date.today()
        chore = Chore(
            household=self.household,
            description="Daily",
            repeat_type="DAILY",
            start_date=start,
            created_by=self.user,
        )

        occurrences = get_occurrences_for_range(
            chore,
            start,
            start + timedelta(days=2),
            completed_dates={start},
            skipped_dates={start + timedelta(days=1)},
        )

        self.assertEqual(len(occurrences), 1)
        self.assertEqual(occurrences[0]["date"], start + timedelta(days=2))
        self.assertFalse(occurrences[0]["is_unscheduled"])
        self.assertFalse(occurrences[0]["is_completed"])


class ChoreViewTests(ChoresBaseTestCase):
    def test_chores_list_requires_active_household(self):
        self.profile.active_household = None
        self.profile.save()

        response = self.client.get(reverse("chores_list"))
        self.assertRedirects(response, reverse("household_settings"))

    def test_chores_list_all_filter_context_and_sorting(self):
        unscheduled = self.create_chore(
            description="Alpha unscheduled",
            has_due_date=False,
            due_date=None,
        )
        unscheduled.assignees.add(self.user)

        scheduled = self.create_chore(
            description="Beta scheduled",
            due_date=date.today() + timedelta(days=1),
            due_time=time(9, 0),
        )
        scheduled.assignees.add(self.other_user)

        daily = self.create_chore(
            description="Daily recurring",
            repeat_type="DAILY",
            has_due_date=False,
            due_date=None,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
        )
        daily.assignees.add(self.user)

        ChoreCompletion.objects.create(
            chore=daily,
            occurrence_date=date.today(),
            completed_by=self.user,
        )
        ChoreSkip.objects.create(
            chore=scheduled,
            occurrence_date=scheduled.due_date,
            skipped_by=self.user,
        )

        response = self.client.get(reverse("chores_list"), {"time_filter": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/chores.html")
        self.assertIn("form", response.context)
        self.assertEqual(response.context["active_household"], self.household)
        self.assertEqual(response.context["time_filter"], "all")

        occurrences = response.context["occurrences"]
        self.assertEqual(occurrences[0]["chore"], unscheduled)

        descriptions = [item["chore"].description for item in occurrences]
        self.assertIn("Daily recurring", descriptions)
        self.assertNotIn("Beta scheduled", descriptions)
        self.assertEqual(descriptions.count("Daily recurring"), 3)

    def test_chores_list_today_filter_with_member_filter(self):
        chore = self.create_chore(description="User chore", due_date=date.today())
        chore.assignees.add(self.user)

        other = self.create_chore(description="Other chore", due_date=date.today())
        other.assignees.add(self.other_user)

        response = self.client.get(
            reverse("chores_list"),
            {"time_filter": "today", "member": str(self.user.id)},
        )

        self.assertEqual(len(response.context["occurrences"]), 1)
        self.assertEqual(response.context["occurrences"][0]["chore"], chore)

    def test_chores_list_week_filter(self):
        chore = self.create_chore(
            description="Weekly view chore", due_date=date.today()
        )
        response = self.client.get(reverse("chores_list"), {"time_filter": "week"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            chore, [item["chore"] for item in response.context["occurrences"]]
        )

    def test_add_chore_get_redirects(self):
        response = self.client.get(reverse("add_chore"))
        self.assertRedirects(response, reverse("chores_list"))

    def test_add_chore_requires_active_household(self):
        self.profile.active_household = None
        self.profile.save()

        response = self.client.post(reverse("add_chore"), {})
        self.assertRedirects(response, reverse("household_settings"))

    def test_add_chore_invalid_form_redirects_without_creating(self):
        count_before = Chore.objects.count()

        response = self.client.post(
            reverse("add_chore"),
            {"description": "Bad weekly", "repeat_type": "WEEKLY"},
        )

        self.assertRedirects(response, reverse("chores_list"))
        self.assertEqual(Chore.objects.count(), count_before)

    def test_add_chore_creates_one_time_daily_and_weekly(self):
        response_one = self.client.post(
            reverse("add_chore"),
            {
                "description": "One-time",
                "repeat_type": "ONE_TIME",
            },
        )
        self.assertRedirects(response_one, reverse("chores_list"))
        one_time = Chore.objects.get(description="One-time")
        self.assertIsNone(one_time.start_date)
        self.assertIsNone(one_time.end_date)
        self.assertFalse(one_time.repeat_monday)

        response_daily = self.client.post(
            reverse("add_chore"),
            {
                "description": "Daily",
                "repeat_type": "DAILY",
                "start_date": date.today().isoformat(),
            },
        )
        self.assertRedirects(response_daily, reverse("chores_list"))
        daily = Chore.objects.get(description="Daily")
        self.assertIsNone(daily.due_date)
        self.assertFalse(daily.repeat_sunday)

        response_weekly = self.client.post(
            reverse("add_chore"),
            {
                "description": "Weekly",
                "repeat_type": "WEEKLY",
                "start_date": date.today().isoformat(),
                "repeat_monday": "on",
                "assignees": [str(self.user.id)],
            },
        )
        self.assertRedirects(response_weekly, reverse("chores_list"))
        weekly = Chore.objects.get(description="Weekly")
        self.assertIsNone(weekly.due_date)
        self.assertTrue(weekly.repeat_monday)
        self.assertEqual(weekly.assignees.get(), self.user)
        self.assertEqual(ActivityLog.objects.filter(action="CHORE_CREATED").count(), 3)

    def test_edit_chore_requires_active_household(self):
        chore = self.create_chore()
        self.profile.active_household = None
        self.profile.save()

        response = self.client.get(reverse("edit_chore", args=[chore.id]))
        self.assertRedirects(response, reverse("household_settings"))

    def test_edit_chore_get_renders_template(self):
        chore = self.create_chore()

        response = self.client.get(reverse("edit_chore", args=[chore.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/edit_chore.html")
        self.assertEqual(response.context["chore"], chore)

    def test_edit_chore_invalid_post_redirects_back(self):
        chore = self.create_chore(
            repeat_type="DAILY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
        )

        response = self.client.post(
            reverse("edit_chore", args=[chore.id]),
            {
                "description": "Oops",
                "repeat_type": "WEEKLY",
                "start_date": date.today().isoformat(),
            },
        )

        self.assertRedirects(response, reverse("edit_chore", args=[chore.id]))

    def test_edit_chore_updates_one_time_daily_and_weekly(self):
        one = self.create_chore(
            description="Editable one",
            start_date=date.today(),
            end_date=date.today(),
        )
        response_one = self.client.post(
            reverse("edit_chore", args=[one.id]),
            {
                "description": "Editable one updated",
                "repeat_type": "ONE_TIME",
            },
        )
        self.assertRedirects(response_one, reverse("chores_list"))
        one.refresh_from_db()
        self.assertEqual(one.description, "Editable one updated")
        self.assertIsNone(one.start_date)

        daily = self.create_chore(
            description="Editable daily",
            repeat_type="WEEKLY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
            repeat_monday=True,
        )
        response_daily = self.client.post(
            reverse("edit_chore", args=[daily.id]),
            {
                "description": "Editable daily updated",
                "repeat_type": "DAILY",
                "start_date": date.today().isoformat(),
            },
        )
        self.assertRedirects(response_daily, reverse("chores_list"))
        daily.refresh_from_db()
        self.assertEqual(daily.description, "Editable daily updated")
        self.assertFalse(daily.repeat_monday)
        self.assertIsNone(daily.due_date)

        weekly = self.create_chore(
            description="Editable weekly",
            repeat_type="DAILY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
        )
        response_weekly = self.client.post(
            reverse("edit_chore", args=[weekly.id]),
            {
                "description": "Editable weekly updated",
                "repeat_type": "WEEKLY",
                "start_date": date.today().isoformat(),
                "repeat_tuesday": "on",
            },
        )
        self.assertRedirects(response_weekly, reverse("chores_list"))
        weekly.refresh_from_db()
        self.assertEqual(weekly.description, "Editable weekly updated")
        self.assertTrue(weekly.repeat_tuesday)
        self.assertEqual(ActivityLog.objects.filter(action="CHORE_UPDATED").count(), 3)

    def test_delete_chore_get_redirects(self):
        chore = self.create_chore()
        response = self.client.get(reverse("delete_chore", args=[chore.id]))
        self.assertRedirects(response, reverse("chores_list"))

    def test_delete_chore_requires_active_household(self):
        chore = self.create_chore()
        self.profile.active_household = None
        self.profile.save()

        response = self.client.post(reverse("delete_chore", args=[chore.id]))
        self.assertRedirects(response, reverse("household_settings"))

    def test_delete_single_recurring_occurrence_requires_date(self):
        chore = self.create_chore(
            repeat_type="DAILY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
        )

        response = self.client.post(
            reverse("delete_chore", args=[chore.id]),
            {"delete_scope": "occurrence"},
        )

        self.assertRedirects(response, reverse("chores_list"))
        self.assertTrue(Chore.objects.filter(id=chore.id).exists())
        self.assertFalse(ChoreSkip.objects.exists())

    def test_delete_single_recurring_occurrence_creates_skip(self):
        chore = self.create_chore(
            repeat_type="WEEKLY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
            repeat_monday=True,
        )
        occurrence_date = date.today().isoformat()

        response = self.client.post(
            reverse("delete_chore", args=[chore.id]),
            {"delete_scope": "occurrence", "occurrence_date": occurrence_date},
        )

        self.assertRedirects(response, reverse("chores_list"))
        self.assertTrue(Chore.objects.filter(id=chore.id).exists())
        self.assertTrue(
            ChoreSkip.objects.filter(
                chore=chore,
                occurrence_date=date.fromisoformat(occurrence_date),
            ).exists()
        )

    def test_delete_series_deletes_chore(self):
        chore = self.create_chore()

        response = self.client.post(reverse("delete_chore", args=[chore.id]))

        self.assertRedirects(response, reverse("chores_list"))
        self.assertFalse(Chore.objects.filter(id=chore.id).exists())
        self.assertGreaterEqual(
            ActivityLog.objects.filter(action="CHORE_DELETED").count(), 1
        )

    def test_complete_chore_get_redirects(self):
        chore = self.create_chore()
        response = self.client.get(
            reverse("complete_chore_occurrence", args=[chore.id])
        )
        self.assertRedirects(response, reverse("chores_list"))

    def test_complete_chore_requires_active_household(self):
        chore = self.create_chore()
        self.profile.active_household = None
        self.profile.save()

        response = self.client.post(
            reverse("complete_chore_occurrence", args=[chore.id])
        )
        self.assertRedirects(response, reverse("household_settings"))

    def test_complete_recurring_chore_with_explicit_date(self):
        chore = self.create_chore(
            repeat_type="DAILY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
        )
        occurrence_date = date.today().isoformat()

        response = self.client.post(
            reverse("complete_chore_occurrence", args=[chore.id]),
            {"occurrence_date": occurrence_date},
        )

        self.assertRedirects(response, reverse("chores_list"))
        self.assertTrue(
            ChoreCompletion.objects.filter(
                chore=chore,
                occurrence_date=date.fromisoformat(occurrence_date),
            ).exists()
        )
        chore.refresh_from_db()
        self.assertTrue(chore.is_active)

    def test_complete_recurring_chore_without_date_uses_today(self):
        chore = self.create_chore(
            repeat_type="DAILY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
        )

        response = self.client.post(
            reverse("complete_chore_occurrence", args=[chore.id]),
            {},
        )

        self.assertRedirects(response, reverse("chores_list"))
        self.assertTrue(
            ChoreCompletion.objects.filter(
                chore=chore,
                occurrence_date=date.today(),
            ).exists()
        )

    def test_complete_one_time_chore_uses_due_date_and_deactivates(self):
        due = date.today() + timedelta(days=2)
        chore = self.create_chore(due_date=due)

        response = self.client.post(
            reverse("complete_chore_occurrence", args=[chore.id]),
            {},
        )

        self.assertRedirects(response, reverse("chores_list"))
        self.assertTrue(
            ChoreCompletion.objects.filter(chore=chore, occurrence_date=due).exists()
        )
        chore.refresh_from_db()
        self.assertFalse(chore.is_active)
        self.assertGreaterEqual(
            ActivityLog.objects.filter(action="CHORE_COMPLETED").count(),
            1,
        )

    def test_edit_chore_invalid_post_with_field_error_redirects_back(self):
        chore = self.create_chore(
            description="Editable recurring",
            repeat_type="DAILY",
            has_due_date=False,
            due_date=None,
            start_date=date.today(),
        )

        response = self.client.post(
            reverse("edit_chore", args=[chore.id]),
            {
                "description": "Still recurring",
                "repeat_type": "DAILY",
                # intentionally omit start_date to trigger a field error
            },
        )

        self.assertRedirects(response, reverse("edit_chore", args=[chore.id]))
