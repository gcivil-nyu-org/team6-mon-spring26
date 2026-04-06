from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from .models import ActivityLog
from chores.models import Chore
from chores.views import get_occurrences_for_range
from datetime import date, timedelta


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
            events.append(
                {
                    "id": f"{chore.id}-{occ['date']}",
                    "title": f"{chore.description}",
                    "start": occ["date"].isoformat(),
                    "allDay": True,
                    "color": (
                        "#3b82f6"
                        if request.user in chore.assignees.all()
                        else "#94a3b8"
                    ),
                    "extendedProps": {
                        "chore_id": chore.id,
                        "assignees": ", ".join(
                            [u.username for u in chore.assignees.all()]
                        ),
                    },
                }
            )
    return JsonResponse(events, safe=False)


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
