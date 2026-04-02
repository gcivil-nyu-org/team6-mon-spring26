from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from .models import ActivityLog


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
