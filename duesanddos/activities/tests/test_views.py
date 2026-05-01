from django.test import TestCase, RequestFactory
from django.urls import reverse
from accounts.models import CustomUser, Profile
from activities.views import sync_to_google, push_to_google_calendar
from households.models import Household, HouseholdMember
from chores.models import Chore, ChoreCompletion
from unittest.mock import patch, MagicMock
from django.utils import timezone
import datetime
import json


class ActivitiesViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUser.objects.create_user(
            username="act_user", password="testpassword", email="act@a.com"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.client.login(username="act_user", password="testpassword")

        self.household = Household.objects.create(name="Act House")
        self.profile.active_household = self.household
        self.profile.save()
        self.member = HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )

    @patch("activities.views.GoogleCalendarService")
    def test_calendar_view_authenticated(self, MockGoogleCalendarService):
        mock_service = MagicMock()
        mock_service.service = True
        MockGoogleCalendarService.return_value = mock_service

        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)

    def test_calendar_events_api_no_household(self):
        self.profile.active_household = None
        self.profile.save()
        response = self.client.get(reverse("calendar_events_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_calendar_events_api_unassigned_member_filtered(self):
        Chore.objects.create(
            description="Filtered Chore",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
            start_date="2026-04-01",
        )
        response = self.client.get(reverse("calendar_events_api"), {"user_id": 9999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("django.utils.timezone.now")
    def test_calendar_events_api_with_chore_states(self, mock_tz_now):
        fixed_now = timezone.make_aware(datetime.datetime(2026, 4, 10, 12, 0, 0))
        mock_tz_now.return_value = fixed_now

        # Completed On-Time Chore
        chore_on_time = Chore.objects.create(
            description="On Time Chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            due_date=fixed_now.date(),
            has_due_date=True,
            due_time=datetime.time(14, 0),
        )
        chore_on_time.assignees.add(self.user)
        ChoreCompletion.objects.create(
            chore=chore_on_time,
            occurrence_date=fixed_now.date(),
            completed_by=self.user,
        )
        # Update completed_at to be earlier than due_time for testing on_time correctly.
        comp = ChoreCompletion.objects.get(chore=chore_on_time)
        comp.completed_at = timezone.make_aware(
            datetime.datetime(2026, 4, 10, 10, 0, 0)
        )
        comp.save()

        # Completed Late Chore
        chore_late = Chore.objects.create(
            description="Late Chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            due_date=fixed_now.date(),
            has_due_date=True,
            due_time=datetime.time(8, 0),
        )
        chore_late.assignees.add(self.user)
        ChoreCompletion.objects.create(
            chore=chore_late, occurrence_date=fixed_now.date(), completed_by=self.user
        )
        comp2 = ChoreCompletion.objects.get(chore=chore_late)
        comp2.completed_at = timezone.make_aware(
            datetime.datetime(2026, 4, 10, 10, 0, 0)
        )
        comp2.save()

        # Overdue Chore
        chore_overdue = Chore.objects.create(
            description="Overdue Chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            due_date=fixed_now.date(),
            has_due_date=True,
            due_time=datetime.time(8, 0),  # Missed
        )
        chore_overdue.assignees.add(self.user)

        response = self.client.get(reverse("calendar_events_api"))
        self.assertEqual(response.status_code, 200)
        events = response.json()

        on_time_event = next(
            e for e in events if e["extendedProps"]["chore_id"] == chore_on_time.id
        )
        self.assertEqual(on_time_event["color"], "#10b981")  # Green

        late_event = next(
            e for e in events if e["extendedProps"]["chore_id"] == chore_late.id
        )
        self.assertEqual(late_event["color"], "#f59e0b")  # Yellow

        overdue_event = next(
            e for e in events if e["extendedProps"]["chore_id"] == chore_overdue.id
        )
        self.assertEqual(overdue_event["color"], "#ef4444")  # Red

    def test_calendar_events_api_date_range(self):
        """Test start and end date parameters in calendar API."""
        Chore.objects.create(
            description="Range Chore",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            due_date=datetime.date(2026, 5, 15),
            has_due_date=True,
        )
        # Query for a range that EXCLUDES the chore
        response = self.client.get(
            reverse("calendar_events_api"),
            {"start": "2026-06-01T00:00:00Z", "end": "2026-06-30T00:00:00Z"},
        )
        self.assertEqual(len(response.json()), 0)

        # Query for a range that INCLUDES the chore
        response = self.client.get(
            reverse("calendar_events_api"),
            {"start": "2026-05-01T00:00:00Z", "end": "2026-05-31T00:00:00Z"},
        )
        self.assertEqual(len(response.json()), 1)

    def test_calendar_events_api_invalid_date_range(self):
        """Test fallback when invalid dates are provided."""
        response = self.client.get(
            reverse("calendar_events_api"),
            {"start": "invalid-date", "end": "2026-05-31"},
        )
        self.assertEqual(response.status_code, 200)
        # Should not crash and return results based on default window

    def test_calendar_events_api_completed_one_time_chore(self):
        """Test that inactive but completed one-time chores show on calendar."""
        chore = Chore.objects.create(
            description="Inactive Completed OneTime",
            household=self.household,
            created_by=self.user,
            repeat_type="ONE_TIME",
            due_date=datetime.date(2026, 5, 1),
            has_due_date=True,
            is_active=False,  # Inactive
        )
        # Create a completion
        ChoreCompletion.objects.create(
            chore=chore,
            occurrence_date=datetime.date(2026, 5, 1),
            completed_by=self.user,
        )

        response = self.client.get(
            reverse("calendar_events_api"), {"start": "2026-05-01", "end": "2026-05-02"}
        )
        events = response.json()
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0]["title"], f"{chore.description} (Done by {self.user.username})"
        )
        self.assertEqual(events[0]["backgroundColor"], "#10b981")

    def test_calendar_events_api_inactive_recurring_skipped(self):
        """Test that inactive recurring chores are skipped."""
        Chore.objects.create(
            description="Inactive Recurring",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
            is_active=False,
        )
        response = self.client.get(reverse("calendar_events_api"))
        self.assertEqual(len(response.json()), 0)

    @patch("activities.views.GoogleCalendarService")
    def test_sync_to_google(self, MockGoogleCalendarService):
        mock_service = MagicMock()
        mock_service.service = True
        mock_service.sync_chore.return_value = {"id": "123"}
        MockGoogleCalendarService.return_value = mock_service

        chore = Chore.objects.create(
            description="Sync GCal",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
        )

        request = self.factory.post("/fake/")
        request.user = self.user

        response = sync_to_google(request, chore.id, "2026-04-06")
        self.assertEqual(response.status_code, 200)

        # Test no Google Account
        mock_service.service = False
        response = sync_to_google(request, chore.id, "2026-04-06")
        self.assertEqual(response.status_code, 400)

        # Test Sync Failed
        mock_service.service = True
        mock_service.sync_chore.return_value = None
        response = sync_to_google(request, chore.id, "2026-04-06")
        self.assertEqual(response.status_code, 500)

    @patch("activities.views.GoogleCalendarService")
    def test_push_to_google_calendar(self, MockGoogleCalendarService):
        mock_service = MagicMock()
        mock_service.service = True
        mock_service.sync_chore.return_value = {"id": "123"}
        MockGoogleCalendarService.return_value = mock_service

        chore = Chore.objects.create(
            description="Push GCal",
            household=self.household,
            created_by=self.user,
            repeat_type="DAILY",
        )

        request = self.factory.post("/fake/")
        request.user = self.user

        result = push_to_google_calendar(request, {"chore": chore})
        self.assertEqual(result, "123")

        # Test push without service
        mock_service.service = False
        result = push_to_google_calendar(request, {"chore": chore})
        self.assertIsNone(result)

        # Test push when sync fails
        mock_service.service = True
        mock_service.sync_chore.return_value = None
        result = push_to_google_calendar(request, {"chore": chore})
        self.assertIsNone(result)

    def test_activity_feed_view(self):
        response = self.client.get(reverse("activity_feed"))
        self.assertEqual(response.status_code, 200)

        self.profile.active_household = None
        self.profile.save()
        response = self.client.get(reverse("activity_feed"))
        self.assertEqual(response.status_code, 200)

    def test_activity_log_view_no_household(self):
        """Test redirect when no household is active."""
        self.profile.active_household = None
        self.profile.save()
        response = self.client.get(reverse("activity_log"))
        self.assertRedirects(response, reverse("household_settings"))

    def test_activity_log_view_filters(self):
        """Test activity log with date and action filters."""
        from activities.models import ActivityLog

        ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="CHORE_CREATED",
            details="Test",
        )
        response = self.client.get(
            reverse("activity_log"),
            {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "action": "CHORE_CREATED",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CHORE_CREATED")

    def test_activity_log_view_invalid_date(self):
        response = self.client.get(reverse("activity_log"), {"start_date": "invalid"})
        self.assertEqual(response.status_code, 200)

    def test_update_calendar_view_pref(self):
        """Test updating calendar view preference."""
        data = {"view": "timeGridWeek"}
        response = self.client.post(
            reverse("update_calendar_view_pref"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.default_calendar_view, "timeGridWeek")

    def test_update_calendar_view_pref_invalid(self):
        """Test updating preference with invalid method and data."""
        # Test GET (should fail)
        response = self.client.get(reverse("update_calendar_view_pref"))
        self.assertEqual(response.status_code, 400)

        # Test invalid JSON
        response = self.client.post(
            reverse("update_calendar_view_pref"),
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        # Test invalid view name
        data = {"view": "invalidView"}
        response = self.client.post(
            reverse("update_calendar_view_pref"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
