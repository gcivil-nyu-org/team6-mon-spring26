from datetime import datetime, time, timedelta

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
    def _get_service(self):
        token_obj = (
            SocialToken.objects.filter(
                account__user=self.user, account__provider="google"
            )
            .select_related("app")
            .first()
        )

        if not token_obj:
            return None

        creds = Credentials(
            token=token_obj.token,
            refresh_token=token_obj.token_secret or None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_obj.app.client_id,
            client_secret=token_obj.app.secret,
        )

        # Refresh if expired or about to expire (within 5 min)
        now = timezone.now()
        if creds.expired or (
            creds.expiry
            and timezone.make_aware(creds.expiry, timezone=timezone.utc)
            < now + timedelta(minutes=5)
        ):
            try:
                creds.refresh(Request())
                # Persist the refreshed token back to the DB
                token_obj.token = creds.token
                if creds.expiry:
                    token_obj.expires_at = timezone.make_aware(
                        creds.expiry, timezone=timezone.utc
                    )
                token_obj.save(update_fields=["token", "expires_at"])
            except Exception as e:  # pragma: no cover
                logger.error(f"Token refresh failed for {self.user.username}: {e}")
                return None

        try:
            return build("calendar", "v3", credentials=creds)
        except Exception as e:  # pragma: no cover
            logger.error(f"Failed to build GCal service for {self.user.username}: {e}")
            return None

    # -------------------------------------------------------------- helpers
    def _get_recurrence_rule(self, chore):
        if chore.repeat_type == "DAILY":
            rule = "RRULE:FREQ=DAILY"
            if chore.end_date:
                rule += f";UNTIL={chore.end_date.strftime('%Y%m%dT235959Z')}"
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
                rule += f";UNTIL={chore.end_date.strftime('%Y%m%dT235959Z')}"
            return [rule]
        return None

    def _build_event_body(self, chore, status_prefix=""):
        """Build the Google Calendar event body dict for a chore."""
        if chore.repeat_type == "ONE_TIME":
            start_date = chore.due_date or timezone.now().date()
        else:
            start_date = chore.start_date or timezone.now().date()

        target_time = chore.due_time or time(9, 0)
        start_dt = datetime.combine(start_date, target_time)
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
        event_body = {
            "summary": summary,
            "description": (
                f"📌 Synced from Dues & Do's\n"
                f"🏠 Household: {chore.household.name}\n"
                f"👥 Assigned to: {assignees}"
            ),
            "start": {"dateTime": aware_start.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
            "reminders": {"useDefault": True},
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
                event = (
                    self.service.events()
                    .patch(
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
