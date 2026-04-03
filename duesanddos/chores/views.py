from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from activities.models import ActivityLog
from households.models import HouseholdMember
from .forms import ChoreForm
from .models import Chore


def daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def get_occurrences_for_range(chore, start_date, end_date):
    occurrences = []
    for day in daterange(start_date, end_date):
        if chore.occurs_on(day):
            occurrences.append(
                {
                    "chore": chore,
                    "date": day,
                    "is_unscheduled": False,
                }
            )
    return occurrences


@login_required
def chores_list_view(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect("household_settings")

    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    time_filter = request.GET.get("time_filter", "today")
    member_filter = request.GET.get("member", "").strip()

    if time_filter == "week":
        range_start, range_end = start_of_week, end_of_week
    elif time_filter == "all":
        range_start, range_end = today - timedelta(days=30), today + timedelta(days=90)
    else:
        range_start = range_end = today

    chores = (
        Chore.objects.filter(household=active_hh, is_active=True)
        .prefetch_related("assignees")
        .order_by("description")
    )

    members = HouseholdMember.objects.filter(household=active_hh).select_related("user")

    occurrences = []

    for chore in chores:
        assignee_ids = list(chore.assignees.values_list("id", flat=True))

        if member_filter and int(member_filter) not in assignee_ids:
            continue

        occurrences.extend(get_occurrences_for_range(chore, range_start, range_end))

        # Show unscheduled one-time chores only in the "all chores" view
        if (
            time_filter == "all"
            and chore.repeat_type == "ONE_TIME"
            and not chore.has_due_date
        ):
            occurrences.append(
                {
                    "chore": chore,
                    "date": None,
                    "is_unscheduled": True,
                }
            )

    occurrences.sort(
        key=lambda item: (
            0 if item["is_unscheduled"] else 1,
            item["date"] or date.max,
            item["chore"].due_time or datetime.min.time(),
            item["chore"].description.lower(),
        )
    )

    form = ChoreForm(household=active_hh)

    return render(
        request,
        "accounts/chores.html",
        {
            "form": form,
            "members": members,
            "occurrences": occurrences,
            "time_filter": time_filter,
            "member_filter": member_filter,
            "today": today,
            "active_household": active_hh,
        },
    )


@login_required
@transaction.atomic
def add_chore_view(request):
    if request.method != "POST":
        return redirect("chores_list")

    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect("household_settings")

    form = ChoreForm(request.POST, household=active_hh)

    if not form.is_valid():
        for field, errors in form.errors.items():
            if field == "__all__":
                for error in errors:
                    messages.error(request, error)
            else:
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect("chores_list")

    chore = form.save(commit=False)
    chore.household = active_hh
    chore.created_by = request.user

    if chore.repeat_type == "ONE_TIME":
        # One-time chores don't need recurring window fields
        if not chore.has_due_date:
            chore.due_date = None
        chore.start_date = timezone.localdate()
        chore.end_date = None
        chore.repeat_monday = False
        chore.repeat_tuesday = False
        chore.repeat_wednesday = False
        chore.repeat_thursday = False
        chore.repeat_friday = False
        chore.repeat_saturday = False
        chore.repeat_sunday = False

    elif chore.repeat_type == "DAILY":
        chore.due_date = None
        chore.repeat_monday = False
        chore.repeat_tuesday = False
        chore.repeat_wednesday = False
        chore.repeat_thursday = False
        chore.repeat_friday = False
        chore.repeat_saturday = False
        chore.repeat_sunday = False

    elif chore.repeat_type == "WEEKLY":
        chore.due_date = None

    chore.full_clean()
    chore.save()
    form.save_m2m()

    ActivityLog.objects.create(
        user=request.user,
        household=active_hh,
        action="CHORE_CREATED",
        details=f"Created chore '{chore.description}'.",
    )

    messages.success(request, "Chore created successfully.")
    return redirect("chores_list")


@login_required
def chores_calendar_events(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        return JsonResponse([], safe=False)

    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if not start_str or not end_str:
        return JsonResponse([], safe=False)

    start_date = date.fromisoformat(start_str[:10])
    end_date = date.fromisoformat(end_str[:10])

    chores = (
        Chore.objects.filter(household=active_hh, is_active=True)
        .prefetch_related("assignees")
        .order_by("description")
    )

    events = []

    for chore in chores:
        for item in get_occurrences_for_range(chore, start_date, end_date):
            assignee_names = ", ".join(
                user.username for user in chore.assignees.all()
            ) or "Unassigned"

            if chore.due_time:
                start_dt = datetime.combine(item["date"], chore.due_time)
                events.append(
                    {
                        "title": f"{chore.description} — {assignee_names}",
                        "start": start_dt.isoformat(),
                        "allDay": False,
                    }
                )
            else:
                events.append(
                    {
                        "title": f"{chore.description} — {assignee_names}",
                        "start": item["date"].isoformat(),
                        "allDay": True,
                    }
                )

    return JsonResponse(events, safe=False)