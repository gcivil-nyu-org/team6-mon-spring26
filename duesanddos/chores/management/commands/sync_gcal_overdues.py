from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time

from chores.models import Chore
from chores.views import get_occurrences_for_range
from activities.google_calendar import GoogleCalendarService


class Command(BaseCommand):
    help = "Finds overdue chore occurrences and syncs their status to Google Calendar"

    def handle(self, *args, **kwargs):
        self.stdout.write("Running Google Calendar overdue sync...")

        # We look around a 14-day window for overdues
        # (It's inefficient to look back infinitely for recurring events)
        start_date = timezone.now().date() - timezone.timedelta(days=14)
        end_date = timezone.now().date()

        active_chores = Chore.objects.filter(is_active=True).prefetch_related(
            "assignees", "completions"
        )
        now = timezone.now()

        updated_count = 0

        for chore in active_chores:
            occurrences = get_occurrences_for_range(chore, start_date, end_date)

            # Get completion dates for this chore to skip checking them
            completed_dates = set(
                chore.completions.values_list("occurrence_date", flat=True)
            )

            for occ in occurrences:
                occ_date = occ["date"]
                if occ_date in completed_dates:
                    continue  # pragma: no cover

                target_time = chore.due_time or time(23, 59, 59)
                try:
                    due_dt = timezone.make_aware(
                        datetime.combine(occ_date, target_time)
                    )
                except ValueError:  # pragma: no cover
                    due_dt = datetime.combine(occ_date, target_time)

                if now > due_dt:
                    # It's overdue! Sync to all assignees
                    sync_success = False
                    for user in chore.assignees.all():
                        service = GoogleCalendarService(user)
                        if service.service:
                            if service.mark_occurrence_overdue(chore, occ_date):
                                sync_success = True

                    if sync_success:
                        updated_count += 1
                        self.stdout.write(
                            f"Marked overdue for: '{chore.description}' on {occ_date}"
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. Updated {updated_count} overdue occurrences."
            )
        )
