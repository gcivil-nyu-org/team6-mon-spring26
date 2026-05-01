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
        {
            "members": members,
            "active_household": active_hh,
            "default_calendar_view": request.user.profile.default_calendar_view,
        },
    )


@login_required
def calendar_events_api(request):
    """JSON feed for FullCalendar (#36)."""
    active_hh = request.user.profile.active_household
    if not active_hh:
        return JsonResponse([], safe=False)

    # Use FullCalendar's range if provided, else fallback to a wide window
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    try:
        if start_str:
            start_date = datetime.fromisoformat(start_str.split("T")[0]).date()
        else:
            start_date = date.today() - timedelta(days=365)

        if end_str:
            end_date = datetime.fromisoformat(end_str.split("T")[0]).date()
        else:
            end_date = date.today() + timedelta(days=365)
    except (ValueError, IndexError):
        start_date = date.today() - timedelta(days=365)
        end_date = date.today() + timedelta(days=365)

    # Include both active chores AND completed one-time chores (is_active=False)
    chores = Chore.objects.filter(household=active_hh).prefetch_related("assignees")

    # Fetch completions to map them to occurrences
    completions = ChoreCompletion.objects.filter(
        chore__household=active_hh, occurrence_date__range=(start_date, end_date)
    ).select_related("completed_by")

    completion_map = {(c.chore_id, c.occurrence_date): c for c in completions}

    # member_id: None means All, "" (from select) means All
    member_id = request.GET.get("user_id")

    events = []
    for chore in chores:
        # Filter by member if specified
        if member_id and member_id != "":
            if not chore.assignees.filter(id=member_id).exists():
                continue

        # For completed one-time chores, the chore is inactive but we still want
        # to show it on its due_date (with "Completed" status from completions)
        if not chore.is_active and chore.repeat_type == "ONE_TIME":
            # Show on the due_date if it has one and it falls in range
            if chore.has_due_date and chore.due_date:
                if start_date <= chore.due_date <= end_date:
                    occ_date = chore.due_date
                    comp = completion_map.get((chore.id, occ_date))
                    color = "#10b981"  # Green (completed)
                    status = "Completed"
                    display_title = chore.description
                    if comp:
                        display_title = f"{chore.description} (Done by {comp.completed_by.username})"
                    events.append({
                        "id": f"{chore.id}-{occ_date}",
                        "title": display_title,
                        "start": occ_date.isoformat(),
                        "allDay": True,
                        "backgroundColor": color,
                        "borderColor": color,
                        "extendedProps": {
                            "chore_id": chore.id,
                            "assignees": ", ".join([u.username for u in chore.assignees.all()]),
                            "completed_by": comp.completed_by.username if comp else None,
                            "status": status,
                        }
                    })
            continue  # Skip further processing for inactive chores

        if not chore.is_active:
            continue  # Skip inactive recurring chores

        # Get occurrences for active chores
        occurrences = get_occurrences_for_range(chore, start_date, end_date)

        for occ in occurrences:
            occ_date = occ["date"]
            comp = completion_map.get((chore.id, occ_date))

            # Default Status
            color = "#3b82f6"  # Blue
            status = "Pending"
            display_title = chore.description

            target_time = chore.due_time or datetime.max.time()
            due_datetime = timezone.make_aware(datetime.combine(occ_date, target_time))

            if comp:
                status = "Completed"
                display_title = f"{chore.description} (Done by {comp.completed_by.username})"
                if comp.completed_at > due_datetime:
                    color = "#f59e0b"  # Yellow
                else:
                    color = "#10b981"  # Green
            elif timezone.now() > due_datetime:
                status = "Overdue"
                color = "#ef4444"  # Red
                display_title = f"{chore.description} (Overdue)"

            events.append({
                "id": f"{chore.id}-{occ_date}",
                "title": display_title,
                "start": occ_date.isoformat(),
                "allDay": True,
                "color": color,  # Added back for test compatibility
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {
                    "chore_id": chore.id,
                    "assignees": ", ".join([u.username for u in chore.assignees.all()]),
                    "completed_by": comp.completed_by.username if comp else None,
                    "status": status,
                }
            })
    return JsonResponse(events, safe=False)


@login_required
def sync_to_google(request, chore_id, date_str):
    """Pushes a chore occurrence to the user's Google Calendar."""
    from accounts.models import Profile

    profile, _ = Profile.objects.get_or_create(user=request.user)
    chore = get_object_or_404(Chore, id=chore_id, household=profile.active_household)
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
    from accounts.models import Profile

    profile, _ = Profile.objects.get_or_create(user=request.user)
    active_hh = profile.active_household
    if not active_hh:
        activities = []
    else:
        activities = ActivityLog.objects.filter(household=active_hh).order_by(
            "-timestamp"
        )[:50]

    return render(request, "activities/activity_feed.html", {"activities": activities})


@login_required
def update_calendar_view_pref(request):
    """Saves the user's last selected calendar view (Month/Week/Day)."""
    if request.method == "POST":
        import json
        from accounts.models import Profile

        try:
            data = json.loads(request.body)
            new_view = data.get("view")
            # Validate against Profile choices
            valid_views = [choice[0] for choice in Profile.DEFAULT_VIEW_CHOICES]
            if new_view in valid_views:
                profile, _ = Profile.objects.get_or_create(user=request.user)
                profile.default_calendar_view = new_view
                profile.save()
                return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "POST required"}, status=400)
