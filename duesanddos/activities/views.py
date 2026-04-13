from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from .models import ActivityLog
from .google_calendar import GoogleCalendarService
from django.http import JsonResponse
from chores.models import Chore, ChoreCompletion
from chores.views import get_occurrences_for_range


@login_required
def activity_log_view(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        return redirect("household_settings")

    today = timezone.now().date()
    default_start = today.replace(day=1)
    default_end = today

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    action_filter = request.GET.get("action")

    try:
        start_date = (
            datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if start_date_str
            else default_start
        )
        end_date = (
            datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date_str
            else default_end
        )
    except ValueError:
        start_date, end_date = default_start, default_end

    raw_activities = ActivityLog.objects.filter(
        household=active_hh, timestamp__date__range=(start_date, end_date)
    )

    if action_filter:
        raw_activities = raw_activities.filter(action=action_filter)

    raw_activities = raw_activities.order_by("-timestamp")

    page_number = request.GET.get("page")
    paginator = Paginator(raw_activities, 10)
    activities_page = paginator.get_page(page_number)

    return render(
        request,
        "accounts/activity.html",
        {
            "activities": activities_page,
            "active_household": active_hh,
            "start_date": start_date,
            "end_date": end_date,
            "current_action": action_filter,
            "action_choices": ActivityLog.ACTION_CHOICES,
        },
    )


@login_required
def calendar_view(request):
    """Renders the calendar page with roommate filters (#39, #41)."""
    active_hh = request.user.profile.active_household
    members = active_hh.members.all() if active_hh else []
    return render(
        request,
        "activities/calendar.html",
        {"members": members, "active_household": active_hh},
    )


@login_required
def calendar_events_api(request):
    """JSON feed for FullCalendar (#36)."""
    active_hh = request.user.profile.active_household
    if not active_hh:
        return JsonResponse([], safe=False)

    # Use a broad range for the calendar view
    start_date = date.today() - timedelta(days=60)
    end_date = date.today() + timedelta(days=90)

    chores = Chore.objects.filter(household=active_hh, is_active=True).prefetch_related(
        "assignees"
    )

    # Fetch completions to map them to occurrences
    completions = ChoreCompletion.objects.filter(
        chore__household=active_hh, occurrence_date__range=(start_date, end_date)
    ).select_related("completed_by")

    completion_map = {(c.chore_id, c.occurrence_date): c for c in completions}

    # Filter by roommate (#39)
    member_id = request.GET.get("user_id")

    events = []
    for chore in chores:
        # Skip if filter is active and user is not an assignee
        if member_id and not chore.assignees.filter(id=member_id).exists():
            continue

        # Get occurrences using teammate's logic
        occurrences = get_occurrences_for_range(chore, start_date, end_date)

        for occ in occurrences:
            occ_date = occ["date"]
            comp = completion_map.get((chore.id, occ_date))

            # Default Status: Upcoming or Today
            color = "#3b82f6"  # Blue
            display_title = chore.description

            # Combine occurrence date and due time into a datetime object for comparison
            # If no due time, assume 23:59:59 of that day
            target_time = chore.due_time or datetime.max.time()
            due_datetime = timezone.make_aware(datetime.combine(occ_date, target_time))

            if comp:
                done_by = comp.completed_by.username
                # Show done by in title or tooltip
                display_title = f"{chore.description} (Done by {done_by})"

                if comp.completed_at > due_datetime:
                    # Completed LATE
                    color = "#f59e0b"  # Yellow
                else:
                    # Completed ON TIME
                    color = "#10b981"  # Green
            elif timezone.now() > due_datetime:
                # OVERDUE (Past due date/time and not completed)
                color = "#ef4444"  # Red
                display_title = f"{chore.description} (Overdue)"

            events.append(
                {
                    "id": f"{chore.id}-{occ_date}",
                    "title": display_title,
                    "start": occ_date.isoformat(),
                    "allDay": True,
                    "color": color,
                    "extendedProps": {
                        "chore_id": chore.id,
                        "assignees": ", ".join(
                            [u.username for u in chore.assignees.all()]
                        ),
                        "completed_by": comp.completed_by.username if comp else None,
                        "status": (
                            "Completed"
                            if comp
                            else (
                                "Overdue"
                                if timezone.now() > due_datetime
                                else "Pending"
                            )
                        ),
                    },
                }
            )
    return JsonResponse(events, safe=False)


@login_required
def sync_to_google(request, chore_id, date_str):
    """Pushes a chore occurrence to the user's Google Calendar."""
    chore = get_object_or_404(
        Chore, id=chore_id, household=request.user.profile.active_household
    )
    service = GoogleCalendarService(request.user)

    if not service.service:
        return JsonResponse({"error": "Google account not linked"}, status=400)

    event = service.sync_chore(chore)
    if event:
        return JsonResponse({"status": "synced", "event_id": event.get("id")})
    return JsonResponse({"error": "Sync failed"}, status=500)


def push_to_google_calendar(request, chore_occurrence):
    """Push a single chore occurrence to Google Calendar."""
    service = GoogleCalendarService(request.user)
    if not service.service:
        return None

    chore = chore_occurrence["chore"]
    event = service.sync_chore(chore)
    return event.get("id") if event else None


@login_required
def activity_feed_view(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        activities = []
    else:
        activities = ActivityLog.objects.filter(household=active_hh).order_by(
            "-timestamp"
        )[:50]

    return render(request, "activities/activity_feed.html", {"activities": activities})
