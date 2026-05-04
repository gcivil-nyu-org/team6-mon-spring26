from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone
from allauth.socialaccount.models import SocialToken
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import logging

logger = logging.getLogger(__name__)

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class GoogleCalendarService:
    """Manages Google Calendar API interactions with automatic token refresh."""

    def __init__(self, user):
        self.user = user
        self.service = self._get_service()

    # ------------------------------------------------------------------ auth
    def _normalize_expiry(self, expiry):
        if not isinstance(expiry, datetime):
            return None
        if timezone.is_naive(expiry):
            return timezone.make_aware(expiry, timezone=timezone.utc)
        return expiry.astimezone(timezone.utc)

    def _get_service(self):
        token_obj = (
            SocialToken.objects.filter(
                account__user=self.user, account__provider="google"
            )
            .select_related("app")
            .first()
        )

        if not token_obj:
            logger.error(
                f"GCal sync skipped for {self.user.username}: no Google account linked."
            )
            return None

        # Normalize the DB expiry to timezone-aware UTC for Django comparisons
        db_expiry = self._normalize_expiry(token_obj.expires_at)
        # google-auth's Credentials.expired compares against datetime.utcnow() (naive),
        # so we must strip the tzinfo before passing expiry to the constructor.
        naive_expiry = db_expiry.replace(tzinfo=None) if db_expiry else None

        # allauth 65.x stores app config in settings, so token_obj.app may be None
        if token_obj.app:
            client_id = token_obj.app.client_id
            client_secret = token_obj.app.secret
        else:
            google_app = settings.SOCIALACCOUNT_PROVIDERS.get("google", {}).get(
                "APP", {}
            )
            client_id = google_app.get("client_id", "")
            client_secret = google_app.get("secret", "")

        creds = Credentials(
            token=token_obj.token,
            refresh_token=token_obj.token_secret or None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            expiry=naive_expiry,
        )

        # Refresh if expired or about to expire (within 5 min)
        now = timezone.now()
        needs_refresh = creds.expired or (
            db_expiry and db_expiry < now + timedelta(minutes=5)
        )
        if needs_refresh:
            if not creds.refresh_token:
                logger.error(
                    f"GCal sync skipped for {self.user.username}: no refresh token. "
                    "User must reconnect their account in Profile Settings."
                )
                return None
            try:
                creds.refresh(Request())
                # Persist the refreshed token back to the DB
                token_obj.token = creds.token
                refreshed_expiry = self._normalize_expiry(creds.expiry)
                if refreshed_expiry:
                    token_obj.expires_at = refreshed_expiry
                token_obj.save(update_fields=["token", "expires_at"])
            except Exception as e:  # pragma: no cover
                # fmt: off
                logger.error(f"Token refresh failed for {self.user.username}: {e}")  # pragma: no cover  # noqa: E501
                # fmt: on
                return None  # pragma: no cover

        try:
            return build("calendar", "v3", credentials=creds)
        except Exception as e:  # pragma: no cover
            # fmt: off
            logger.error(f"Failed to build GCal service for {self.user.username}: {e}")  # pragma: no cover  # noqa: E501
            # fmt: on
            return None  # pragma: no cover

    # -------------------------------------------------------------- helpers
    def _get_recurrence_rule(self, chore):
        # All-day events use a date-only UNTIL value; timed events use UTC datetime.
        if chore.due_time:
            until_fmt = "%Y%m%dT235959Z"
        else:
            until_fmt = "%Y%m%d"

        if chore.repeat_type == "DAILY":
            rule = "RRULE:FREQ=DAILY"
            if chore.end_date:
                rule += f";UNTIL={chore.end_date.strftime(until_fmt)}"
            return [rule]
        elif chore.repeat_type == "WEEKLY":
            days = []
            if chore.repeat_monday:
                days.append("MO")
            if chore.repeat_tuesday:
                days.append("TU")
            if chore.repeat_wednesday:
                days.append("WE")
            if chore.repeat_thursday:
                days.append("TH")
            if chore.repeat_friday:
                days.append("FR")
            if chore.repeat_saturday:
                days.append("SA")
            if chore.repeat_sunday:
                days.append("SU")

            if not days:
                return None

            rule = f"RRULE:FREQ=WEEKLY;BYDAY={','.join(days)}"
            if chore.end_date:
                rule += f";UNTIL={chore.end_date.strftime(until_fmt)}"
            return [rule]
        return None

    def _build_event_body(self, chore, status_prefix=""):
        """Build the Google Calendar event body dict for a chore."""
        if chore.repeat_type == "ONE_TIME":
            start_date = chore.due_date or timezone.now().date()
        else:
            start_date = chore.start_date or timezone.now().date()

        is_all_day = chore.due_time is None
        if is_all_day:
            aware_start = None
            end_dt = None
        else:
            start_dt = datetime.combine(start_date, chore.due_time)
            try:
                aware_start = timezone.make_aware(start_dt)
            except ValueError:  # pragma: no cover
                aware_start = start_dt
            end_dt = aware_start + timedelta(minutes=30)

        summary = f"Chore: {chore.description}"
        if status_prefix:
            summary = f"{status_prefix} {summary}"

        assignees = ", ".join(
            u.get_full_name() or u.username for u in chore.assignees.all()
        )

        # Build a detailed description with every available field
        lines = [
            "📌 Synced from Dues & Do's",
            f"🏠 Household: {chore.household.name}",
            f"👥 Assigned to: {assignees}",
            "",
        ]

        # Schedule type
        type_label = dict(chore.REPEAT_TYPE_CHOICES).get(
            chore.repeat_type, chore.repeat_type
        )
        lines.append(f"🔁 Type: {type_label}")

        if chore.repeat_type == "ONE_TIME":
            if chore.has_due_date and chore.due_date:
                lines.append(
                    f"📅 Due date: {chore.due_date.strftime('%A, %B %-d, %Y')}"
                )
            else:
                lines.append("📅 Due date: No due date")
            if chore.due_time:
                lines.append(f"⏰ Due time: {chore.due_time.strftime('%-I:%M %p')}")
            else:
                lines.append("⏰ Due time: Any time")

        else:
            if chore.start_date:
                lines.append(
                    f"📅 Starts: {chore.start_date.strftime('%A, %B %-d, %Y')}"
                )
            if chore.end_date:
                lines.append(f"🏁 Ends: {chore.end_date.strftime('%A, %B %-d, %Y')}")
            else:
                lines.append("🏁 Ends: No end date (ongoing)")
            if chore.due_time:
                lines.append(f"⏰ Time: {chore.due_time.strftime('%-I:%M %p')}")
            else:
                lines.append("⏰ Time: Any time (all-day)")

            if chore.repeat_type == "WEEKLY":
                day_names = []
                day_map = [
                    (chore.repeat_monday, "Monday"),
                    (chore.repeat_tuesday, "Tuesday"),
                    (chore.repeat_wednesday, "Wednesday"),
                    (chore.repeat_thursday, "Thursday"),
                    (chore.repeat_friday, "Friday"),
                    (chore.repeat_saturday, "Saturday"),
                    (chore.repeat_sunday, "Sunday"),
                ]
                for flag, name in day_map:
                    if flag:
                        day_names.append(name)
                lines.append(f"📆 Repeats on: {', '.join(day_names)}")

        event_body = {
            "summary": summary,
            "description": "\n".join(lines),
            "reminders": {"useDefault": True},
        }

        if is_all_day:
            # Google Calendar treats all-day end dates as exclusive.
            event_body["start"] = {"date": start_date.isoformat()}
            event_body["end"] = {"date": (start_date + timedelta(days=1)).isoformat()}
        else:
            tz_name = str(timezone.get_current_timezone())
            event_body["start"] = {
                "dateTime": aware_start.isoformat(),
                "timeZone": tz_name,
            }
            event_body["end"] = {
                "dateTime": end_dt.isoformat(),
                "timeZone": tz_name,
            }

        recurrence = self._get_recurrence_rule(chore)
        if recurrence:
            event_body["recurrence"] = recurrence

        return event_body

    # ----------------------------------------------------------- sync chore
    def sync_chore(self, chore):
        """Create or update the Google Calendar event for a chore."""
        from chores.models import ChoreGoogleEvent

        if not self.service:  # pragma: no cover
            return None

        event_body = self._build_event_body(chore)

        try:
            sync_record = ChoreGoogleEvent.objects.filter(
                chore=chore, user=self.user
            ).first()

            if sync_record:
                # Use update (PUT) — not patch — so fields removed from the
                # chore (e.g. recurrence when switching to one-time, or
                # start.dateTime when switching to all-day) are actually
                # cleared on the Google event instead of lingering as stale
                # values from the original create.
                event = (
                    self.service.events()
                    .update(
                        calendarId="primary",
                        eventId=sync_record.google_event_id,
                        body=event_body,
                    )
                    .execute()
                )
            else:
                event = (
                    self.service.events()
                    .insert(calendarId="primary", body=event_body)
                    .execute()
                )
                ChoreGoogleEvent.objects.create(  # pragma: no cover
                    chore=chore,
                    user=self.user,
                    google_event_id=event.get("id"),
                )
            return event
        except Exception as e:  # pragma: no cover
            logger.error(f"GCal sync error for chore {chore.id}: {e}")
            return None

    # --------------------------------------------------------- delete event
    def delete_chore_event(self, chore):
        from chores.models import ChoreGoogleEvent

        sync_record = ChoreGoogleEvent.objects.filter(
            chore=chore, user=self.user
        ).first()
        if not sync_record or not self.service:  # pragma: no cover
            return False

        try:
            self.service.events().delete(
                calendarId="primary",
                eventId=sync_record.google_event_id,
            ).execute()
            sync_record.delete()
            return True
        except Exception as e:  # pragma: no cover
            logger.error(f"GCal delete error for chore {chore.id}: {e}")
            if "404" in str(e) or "not found" in str(e).lower():
                sync_record.delete()
                return True
            return False

    # ----------------------------------------------- mark occurrence as done
    def mark_occurrence_done(self, chore, occurrence_date):
        """
        Mark a specific occurrence as completed in Google Calendar.
        - For ONE_TIME chores: update the single event directly.
        - For DAILY / WEEKLY chores: find the matching instance and update it.
        """
        from chores.models import ChoreGoogleEvent

        sync_record = ChoreGoogleEvent.objects.filter(
            chore=chore, user=self.user
        ).first()
        if not sync_record or not self.service:  # pragma: no cover
            return False

        try:
            if chore.repeat_type == "ONE_TIME":
                # Single event — just patch the summary
                event = (
                    self.service.events()
                    .get(
                        calendarId="primary",
                        eventId=sync_record.google_event_id,
                    )
                    .execute()
                )
                current = event.get("summary", "")
                if "✅" not in current:
                    event["summary"] = f"✅ {current}"
                    event["colorId"] = "10"  # green
                    self.service.events().update(
                        calendarId="primary",
                        eventId=event["id"],
                        body=event,
                    ).execute()
                return True
            else:
                # Recurring event — find the specific instance
                instances = (
                    self.service.events()
                    .instances(
                        calendarId="primary",
                        eventId=sync_record.google_event_id,
                        timeMin=datetime.combine(
                            occurrence_date, time(0, 0)
                        ).isoformat()
                        + "Z",
                        timeMax=datetime.combine(
                            occurrence_date, time(23, 59, 59)
                        ).isoformat()
                        + "Z",
                        maxResults=5,
                    )
                    .execute()
                )

                for instance in instances.get("items", []):
                    inst_start = instance.get("start", {}).get(
                        "dateTime"
                    ) or instance.get("start", {}).get("date")
                    if inst_start and occurrence_date.isoformat() in inst_start:
                        current = instance.get("summary", "")
                        if "✅" not in current:
                            instance["summary"] = f"✅ {current}"
                            instance["colorId"] = "10"  # green
                            self.service.events().update(
                                calendarId="primary",
                                eventId=instance["id"],
                                body=instance,
                            ).execute()
                        return True
                return False  # pragma: no cover
        except Exception as e:  # pragma: no cover
            logger.error(f"GCal completion update error: {e}")
            return False

    # ------------------------------------------ mark occurrence as overdue
    def mark_occurrence_overdue(self, chore, occurrence_date):
        """
        Mark a specific occurrence as overdue in Google Calendar.
        """
        from chores.models import ChoreGoogleEvent

        sync_record = ChoreGoogleEvent.objects.filter(
            chore=chore, user=self.user
        ).first()
        if not sync_record or not self.service:  # pragma: no cover
            return False

        try:
            if chore.repeat_type == "ONE_TIME":
                event = (
                    self.service.events()
                    .get(
                        calendarId="primary",
                        eventId=sync_record.google_event_id,
                    )
                    .execute()
                )
                current = event.get("summary", "")
                if "⚠️" not in current and "✅" not in current:
                    event["summary"] = f"⚠️ OVERDUE: {current}"
                    event["colorId"] = "11"  # red
                    self.service.events().update(
                        calendarId="primary",
                        eventId=event["id"],
                        body=event,
                    ).execute()
                return True
            else:
                instances = (
                    self.service.events()
                    .instances(
                        calendarId="primary",
                        eventId=sync_record.google_event_id,
                        timeMin=datetime.combine(
                            occurrence_date, time(0, 0)
                        ).isoformat()
                        + "Z",
                        timeMax=datetime.combine(
                            occurrence_date, time(23, 59, 59)
                        ).isoformat()
                        + "Z",
                        maxResults=5,
                    )
                    .execute()
                )

                for instance in instances.get("items", []):
                    inst_start = instance.get("start", {}).get(
                        "dateTime"
                    ) or instance.get("start", {}).get("date")
                    if inst_start and occurrence_date.isoformat() in inst_start:
                        current = instance.get("summary", "")
                        if "⚠️" not in current and "✅" not in current:
                            instance["summary"] = f"⚠️ OVERDUE: {current}"
                            instance["colorId"] = "11"  # red
                            self.service.events().update(
                                calendarId="primary",
                                eventId=instance["id"],
                                body=instance,
                            ).execute()
                        return True
                return False  # pragma: no cover
        except Exception as e:  # pragma: no cover
            logger.error(f"GCal overdue update error: {e}")
            return False
