import threading
import logging
import sys
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from .models import Chore, ChoreCompletion, ChoreSkip, ChoreGoogleEvent
from activities.google_calendar import GoogleCalendarService

logger = logging.getLogger(__name__)


def run_in_background(target, args=()):
    if "test" in sys.argv:
        target(*args)
    else:
        threading.Thread(target=target, args=args).start()


def sync_chore_to_gcal(chore_id):
    """Background task to sync a chore for all its assignees."""
    try:
        chore = Chore.objects.prefetch_related("assignees").get(id=chore_id)

        if not chore.is_active:
            # If chore became inactive, delete events for all assignees
            for sync in ChoreGoogleEvent.objects.filter(chore=chore).select_related(
                "user"
            ):
                service = GoogleCalendarService(sync.user)
                if service.service:
                    service.delete_chore_event(chore)
            return

        for user in chore.assignees.all():
            service = GoogleCalendarService(user)
            if service.service:
                service.sync_chore(chore)
    except Chore.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Async GCal Sync Error: {e}")


def delete_chore_from_gcal_task(google_sync_data):
    """
    google_sync_data: list of (user_id, google_event_id)
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    for user_id, event_id in google_sync_data:
        try:
            user = User.objects.get(id=user_id)
            service = GoogleCalendarService(user)
            if service.service:
                service.service.events().delete(
                    calendarId="primary", eventId=event_id
                ).execute()
        except Exception as e:
            logger.error(f"Async GCal Delete Error: {e}")


@receiver(post_save, sender=Chore)
def handle_chore_save(sender, instance, created, **kwargs):
    """Triggered on chore creation or update."""
    run_in_background(target=sync_chore_to_gcal, args=(instance.id,))


@receiver(pre_delete, sender=Chore)
def handle_chore_delete(sender, instance, **kwargs):
    """Triggered when a chore series is deleted."""
    sync_data = list(instance.google_events.values_list("user_id", "google_event_id"))
    if sync_data:
        run_in_background(target=delete_chore_from_gcal_task, args=(sync_data,))


@receiver(m2m_changed, sender=Chore.assignees.through)
def handle_assignee_change(sender, instance, action, **kwargs):
    """Triggered when assignees are added/removed."""
    if action in ["post_add", "post_remove", "post_clear"]:
        run_in_background(target=sync_chore_to_gcal, args=(instance.id,))


def update_completion_gcal_task(completion_id):
    """Background task to mark a chore occurrence as done on Google Calendar."""
    try:
        completion = ChoreCompletion.objects.select_related(
            "chore", "completed_by"
        ).get(id=completion_id)
        chore = completion.chore

        # Update for the completer
        service = GoogleCalendarService(completion.completed_by)
        if service.service:
            service.mark_occurrence_done(chore, completion.occurrence_date)

        # Also update for all other assignees who have synced events
        for user in chore.assignees.exclude(id=completion.completed_by_id):
            svc = GoogleCalendarService(user)
            if svc.service:
                svc.mark_occurrence_done(chore, completion.occurrence_date)

    except ChoreCompletion.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Async GCal Completion Error: {e}")


@receiver(post_save, sender=ChoreCompletion)
def handle_chore_completion(sender, instance, created, **kwargs):
    """Triggered when a specific chore occurrence is completed."""
    if created:
        run_in_background(target=update_completion_gcal_task, args=(instance.id,))


def update_skip_gcal_task(skip_id):
    """Background task to remove a skipped occurrence from Google Calendar."""
    try:
        skip = ChoreSkip.objects.select_related("chore", "skipped_by").get(id=skip_id)
        chore = skip.chore

        # For all assignees, delete the specific occurrence
        for user in chore.assignees.all():
            service = GoogleCalendarService(user)
            if not service.service:
                continue

            sync_record = ChoreGoogleEvent.objects.filter(
                chore=chore, user=user
            ).first()
            if not sync_record:
                continue

            try:
                # For recurring events, find and cancel the specific instance
                if chore.repeat_type in ["DAILY", "WEEKLY"]:
                    from datetime import datetime, time

                    instances = (
                        service.service.events()
                        .instances(
                            calendarId="primary",
                            eventId=sync_record.google_event_id,
                            timeMin=datetime.combine(
                                skip.occurrence_date, time(0, 0)
                            ).isoformat()
                            + "Z",
                            timeMax=datetime.combine(
                                skip.occurrence_date, time(23, 59, 59)
                            ).isoformat()
                            + "Z",
                            maxResults=5,
                        )
                        .execute()
                    )
                    for inst in instances.get("items", []):
                        inst_start = inst.get("start", {}).get("dateTime") or inst.get(
                            "start", {}
                        ).get("date")
                        if (
                            inst_start
                            and skip.occurrence_date.isoformat() in inst_start
                        ):
                            inst["status"] = "cancelled"
                            service.service.events().update(
                                calendarId="primary",
                                eventId=inst["id"],
                                body=inst,
                            ).execute()
                            break
            except Exception as e:
                logger.error(
                    f"GCal skip instance cancel error for chore {chore.id}: {e}"
                )

    except ChoreSkip.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Async GCal Skip Error: {e}")


@receiver(post_save, sender=ChoreSkip)
def handle_chore_skip(sender, instance, created, **kwargs):
    """Triggered when a chore occurrence is skipped/deleted."""
    if created:
        run_in_background(target=update_skip_gcal_task, args=(instance.id,))
