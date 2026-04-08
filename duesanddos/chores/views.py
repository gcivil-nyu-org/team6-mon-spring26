import threading
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.core.management import call_command
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from activities.models import ActivityLog
from households.models import HouseholdMember
from .forms import ChoreForm
from .models import Chore, ChoreCompletion, ChoreSkip


def daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def get_occurrences_for_range(
    chore, start_date, end_date, completed_dates=None, skipped_dates=None
):
    completed_dates = completed_dates or set()
    skipped_dates = skipped_dates or set()
    occurrences = []

    for day in daterange(start_date, end_date):
        if (
            chore.occurs_on(day)
            and day not in completed_dates
            and day not in skipped_dates
        ):
            occurrences.append(
                {
                    "chore": chore,
                    "date": day,
                    "is_unscheduled": False,
                    "is_completed": False,
                }
            )

    return occurrences


def run_overdue_sync():
    """Run the management command in the background to ensure overdues are synced."""
    if "test" in sys.argv:
        return
    try:
        call_command("sync_gcal_overdues")
    except Exception:
        pass


@login_required
def chores_list_view(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect("household_settings")

    # Fire and forget overdue sync so Google Calendar stays up to date
    threading.Thread(target=run_overdue_sync).start()

    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    time_filter = request.GET.get("time_filter", "all")
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

    completions = ChoreCompletion.objects.filter(
        chore__household=active_hh,
        occurrence_date__gte=range_start,
        occurrence_date__lte=range_end,
    )

    skips = ChoreSkip.objects.filter(
        chore__household=active_hh,
        occurrence_date__gte=range_start,
        occurrence_date__lte=range_end,
    )

    completed_dates_by_chore = defaultdict(set)
    for completion in completions:
        completed_dates_by_chore[completion.chore_id].add(completion.occurrence_date)

    skipped_dates_by_chore = defaultdict(set)
    for skip in skips:
        skipped_dates_by_chore[skip.chore_id].add(skip.occurrence_date)

    latest_completion_by_chore = {}
    # Fetch all completions for this household, ordered
    all_hh_completions = (
        ChoreCompletion.objects.filter(chore__household=active_hh)
        .select_related("completed_by")
        .order_by("chore_id", "-occurrence_date", "-completed_at")
    )
    for comp in all_hh_completions:
        if comp.chore_id not in latest_completion_by_chore:
            latest_completion_by_chore[comp.chore_id] = comp

    occurrences = []

    for chore in chores:
        assignee_ids = list(chore.assignees.values_list("id", flat=True))

        if member_filter and int(member_filter) not in assignee_ids:
            continue

        completed_dates = completed_dates_by_chore.get(chore.id, set())
        skipped_dates = skipped_dates_by_chore.get(chore.id, set())

        current_ch_occurrences = get_occurrences_for_range(
            chore, range_start, range_end, completed_dates, skipped_dates
        )
        for occ in current_ch_occurrences:
            occ["latest_completion"] = latest_completion_by_chore.get(chore.id)
            occ["member_filter"] = member_filter

        occurrences.extend(current_ch_occurrences)

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
                    "is_completed": False,
                    "latest_completion": latest_completion_by_chore.get(chore.id),
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
            "latest_completions": latest_completion_by_chore,
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
                    messages.error(
                        request, f"{field.replace('_', ' ').title()}: {error}"
                    )
        return redirect("chores_list")

    chore = form.save(commit=False)
    chore.household = active_hh
    chore.created_by = request.user

    if chore.repeat_type == "ONE_TIME":
        if not chore.has_due_date:
            chore.due_date = None
        chore.start_date = None
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
@transaction.atomic
def edit_chore_view(request, chore_id):
    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect("household_settings")

    chore = get_object_or_404(Chore, id=chore_id, household=active_hh)

    if request.method == "POST":
        form = ChoreForm(request.POST, instance=chore, household=active_hh)

        if not form.is_valid():
            for field, errors in form.errors.items():
                if field == "__all__":
                    for error in errors:
                        messages.error(request, error)
                else:
                    for error in errors:
                        messages.error(
                            request, f"{field.replace('_', ' ').title()}: {error}"
                        )
            return redirect("edit_chore", chore_id=chore.id)

        chore = form.save(commit=False)

        if chore.repeat_type == "ONE_TIME":
            if not chore.has_due_date:
                chore.due_date = None
            chore.start_date = None
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
            action="CHORE_UPDATED",
            details=f"Updated chore '{chore.description}'.",
        )

        messages.success(request, "Chore updated successfully.")
        return redirect("chores_list")

    form = ChoreForm(instance=chore, household=active_hh)

    return render(
        request,
        "accounts/edit_chore.html",
        {
            "chore": chore,
            "form": form,
            "members": HouseholdMember.objects.filter(
                household=active_hh
            ).select_related("user"),
        },
    )


@login_required
@transaction.atomic
def delete_chore_view(request, chore_id):
    if request.method != "POST":
        return redirect("chores_list")

    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect("household_settings")

    chore = get_object_or_404(Chore, id=chore_id, household=active_hh)
    delete_scope = request.POST.get("delete_scope", "series")
    occurrence_date_str = request.POST.get("occurrence_date", "").strip()

    if chore.repeat_type in ["DAILY", "WEEKLY"] and delete_scope == "occurrence":
        if not occurrence_date_str:
            messages.error(
                request, "Missing occurrence date for recurring chore deletion."
            )
            return redirect("chores_list")

        occurrence_date = date.fromisoformat(occurrence_date_str)

        ChoreSkip.objects.get_or_create(
            chore=chore,
            occurrence_date=occurrence_date,
            defaults={"skipped_by": request.user},
        )

        ActivityLog.objects.create(
            user=request.user,
            household=active_hh,
            action="CHORE_DELETED",
            details=(
                f"Deleted occurrence of chore '{chore.description}' "
                f"on {occurrence_date.strftime('%-d %B').lower()}."
            ),
        )

        messages.success(request, "This occurrence was deleted.")
        return redirect("chores_list")

    description = chore.description
    chore.delete()

    ActivityLog.objects.create(
        user=request.user,
        household=active_hh,
        action="CHORE_DELETED",
        details=f"Deleted chore '{description}'.",
    )

    messages.success(request, "Chore deleted successfully.")
    return redirect("chores_list")


@login_required
@transaction.atomic
def complete_chore_occurrence_view(request, chore_id):
    if request.method != "POST":
        return redirect("chores_list")

    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect("household_settings")

    chore = get_object_or_404(Chore, id=chore_id, household=active_hh)

    occurrence_date_str = request.POST.get("occurrence_date", "").strip()

    if occurrence_date_str:
        occurrence_date = date.fromisoformat(occurrence_date_str)
    else:
        occurrence_date = chore.due_date or date.today()

    ChoreCompletion.objects.get_or_create(
        chore=chore,
        occurrence_date=occurrence_date,
        defaults={"completed_by": request.user},
    )

    if chore.repeat_type == "ONE_TIME":
        chore.is_active = False
        chore.save(update_fields=["is_active"])

    ActivityLog.objects.create(
        user=request.user,
        household=active_hh,
        details=(
            f"Completed chore '{chore.description}' "
            f"for {occurrence_date.strftime('%-d %B').lower()}."
        ),
    )

    messages.success(request, "Chore marked complete.")
    return redirect("chores_list")
