import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Profile
from chores.models import ChoreCompletion, ChoreSkip
from households.models import Household


def _add_months(first_of_month: date, months: int) -> date:
    year = first_of_month.year + ((first_of_month.month - 1 + months) // 12)
    month = ((first_of_month.month - 1 + months) % 12) + 1
    return date(year, month, 1)


def _month_starts(start_month: date, end_month: date):
    months = []
    current = start_month
    while current <= end_month:
        months.append(current)
        current = _add_months(current, 1)
    return months


def _day_label(value: date) -> str:
    return value.strftime("%b") + f" {value.day}"


def _subtract_one_month(value: date) -> date:
    if value.month == 1:
        target_year = value.year - 1
        target_month = 12
    else:
        target_year = value.year
        target_month = value.month - 1

    try:
        return value.replace(year=target_year, month=target_month)
    except ValueError:
        # Handles dates like March 31 -> February 28/29
        first_of_current_month = value.replace(day=1)
        return first_of_current_month - timedelta(days=1)


@login_required
def insights_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    try:
        active_hh = profile.active_household
    except Household.DoesNotExist:
        active_hh = None
        profile.active_household = None
        profile.save(update_fields=["active_household"])

    if not active_hh:
        return render(request, "insights/index.html", {"no_household": True})

    today = timezone.localdate()
    default_end = today
    default_start = _subtract_one_month(default_end)

    start_date_str = request.GET.get("start_date", default_start.strftime("%Y-%m-%d"))
    end_date_str = request.GET.get("end_date", default_end.strftime("%Y-%m-%d"))

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        start_date = default_start
        end_date = default_end

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    expenses_qs = active_hh.expenses.filter(date_spent__range=(start_date, end_date))
    total_spent = expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    expense_count = expenses_qs.count()

    start_month = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    month_starts = _month_starts(start_month, end_month)
    month_labels = [month.strftime("%b %Y") for month in month_starts]

    monthly_map = {
        row["month"].replace(day=1): float(row["total"] or 0)
        for row in expenses_qs.annotate(month=TruncMonth("date_spent"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    }
    monthly_expenses = [
        monthly_map.get(month_start, 0.0) for month_start in month_starts
    ]

    previous_period_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=previous_period_days - 1)
    previous_total = active_hh.expenses.filter(
        date_spent__range=(prev_start, prev_end)
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    spending_change = 0.0
    if previous_total:
        spending_change = round(
            ((float(total_spent) - float(previous_total)) / float(previous_total))
            * 100,
            1,
        )

    by_member = list(
        expenses_qs.values("payer__username")
        .annotate(total=Sum("amount"), expense_count=Count("id"))
        .order_by("-total", "payer__username")
    )
    member_labels = [row["payer__username"] for row in by_member]
    member_totals = [float(row["total"] or 0) for row in by_member]

    current_month_start = end_date.replace(day=1)
    daily_spend_map = {
        _day_label(row["date_spent"]): float(row["total"] or 0)
        for row in active_hh.expenses.filter(
            date_spent__range=(current_month_start, end_date)
        )
        .values("date_spent")
        .annotate(total=Sum("amount"))
        .order_by("date_spent")
    }
    daily_labels = []
    daily_values = []
    cursor = current_month_start
    while cursor <= end_date:
        label = _day_label(cursor)
        daily_labels.append(label)
        daily_values.append(daily_spend_map.get(label, 0.0))
        cursor += timedelta(days=1)

    chore_window_start = start_date
    chores = active_hh.chores.filter(is_active=True).prefetch_related(
        "assignees", "completions", "skips"
    )

    chore_expected = 0
    chore_completed = 0
    chore_skipped = 0
    member_completion_counts = {}

    completions_in_window = ChoreCompletion.objects.filter(
        chore__household=active_hh,
        occurrence_date__range=(chore_window_start, end_date),
    )
    for row in (
        completions_in_window.values("completed_by__username")
        .annotate(total=Count("id"))
        .order_by("completed_by__username")
    ):
        member_completion_counts[row["completed_by__username"]] = row["total"]

    skip_pairs = set(
        ChoreSkip.objects.filter(
            chore__household=active_hh,
            occurrence_date__range=(chore_window_start, end_date),
        ).values_list("chore_id", "occurrence_date")
    )
    completion_pairs = set(
        completions_in_window.values_list("chore_id", "occurrence_date")
    )

    cursor = chore_window_start
    while cursor <= end_date:
        for chore in chores:
            if chore.occurs_on(cursor):
                chore_expected += 1
                if (chore.id, cursor) in completion_pairs:
                    chore_completed += 1
                elif (chore.id, cursor) in skip_pairs:
                    chore_skipped += 1
        cursor += timedelta(days=1)

    completion_rate = (
        round((chore_completed / chore_expected) * 100, 1) if chore_expected else 0
    )
    open_chore_count = max(chore_expected - chore_completed - chore_skipped, 0)

    insights_cards = {
        "total_spent": float(total_spent),
        "average_expense": (
            round(float(total_spent) / expense_count, 2) if expense_count else 0
        ),
        "previous_total": float(previous_total),
        "spending_change": spending_change,
        "completion_rate": completion_rate,
    }

    context = {
        "active_household": active_hh,
        "start_date": start_date,
        "end_date": end_date,
        "chore_window_start": chore_window_start,
        "insights_cards": insights_cards,
        "monthly_labels_json": json.dumps(month_labels),
        "monthly_expenses_json": json.dumps(monthly_expenses),
        "member_labels_json": json.dumps(member_labels),
        "member_totals_json": json.dumps(member_totals),
        "daily_labels_json": json.dumps(daily_labels),
        "daily_values_json": json.dumps(daily_values),
        "chore_status_labels_json": json.dumps(["Completed", "Skipped", "Open"]),
        "chore_status_values_json": json.dumps(
            [chore_completed, chore_skipped, open_chore_count]
        ),
        "completion_member_labels_json": json.dumps(
            list(member_completion_counts.keys())
        ),
        "completion_member_values_json": json.dumps(
            list(member_completion_counts.values())
        ),
        "top_spenders": by_member[:5],
    }
    return render(request, "insights/index.html", context)
