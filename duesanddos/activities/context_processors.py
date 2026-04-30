from datetime import date, timedelta
from .models import ActivityLog
from chores.models import Chore, ChoreCompletion
from accounts.models import Profile


def activity_notifications(request):
    """Provides recent activities and task reminders for the user."""
    if not request.user.is_authenticated:
        return {}

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    active_hh = profile.active_household
    if not active_hh:
        return {}

    # 1. Fetch recent activities for the household
    recent_activities = (
        ActivityLog.objects.filter(household=active_hh)
        .select_related("user")
        .order_by("-timestamp")[:5]
    )

    # 2. Identify Overdue Chores (Reminders) for the current user
    # Look back 7 days for tasks that were missed
    today = date.today()
    lookback = today - timedelta(days=7)

    # Pre-fetch ALL relevant completions for this lookback window to avoid N+1 queries
    relevant_completions = ChoreCompletion.objects.filter(
        chore__household=active_hh,
        chore__assignees=request.user,
        occurrence_date__gte=lookback,
        occurrence_date__lt=today,
    ).values("chore_id", "occurrence_date")

    # Store in a set for O(1) lookup
    completion_lookup = {
        (c["chore_id"], c["occurrence_date"]) for c in relevant_completions
    }

    overdue_chores = []
    user_chores = Chore.objects.filter(
        household=active_hh, assignees=request.user, is_active=True
    )

    for chore in user_chores:
        current = lookback
        while current < today:
            if chore.occurs_on(current):
                # Use in-memory set instead of database query
                if (chore.id, current) not in completion_lookup:
                    overdue_chores.append({"chore": chore, "date": current})
            current += timedelta(days=1)

    # Sort overdues by date (descending)
    overdue_chores.sort(key=lambda x: x["date"], reverse=True)

    # Total count for the notification badge
    # (Using recent 8 activities + count of distinct overdue chores)
    notification_count = len(
        overdue_chores
    )  # Activity logs aren't marked read, so we only badge the overdue count

    return {
        "recent_notifications": recent_activities,
        "overdue_reminders": overdue_chores[:5],  # Limit to top 5 reminders
        "notification_count": notification_count,
    }
