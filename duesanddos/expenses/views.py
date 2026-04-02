from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from households.models import HouseholdMember
from accounts.models import CustomUser
from activities.models import ActivityLog
from .models import Expense, ExpenseSplit


@login_required
def expenses_list_view(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        return redirect("household_settings")

    expenses = (
        active_hh.expenses.all()
        .select_related("payer")
        .prefetch_related("splits", "splits__user")
        .order_by("-date_spent")
    )
    members = active_hh.members.select_related("user")

    return render(
        request,
        "accounts/expenses.html",
        {"expenses": expenses, "members": members, "active_household": active_hh},
    )


@login_required
@transaction.atomic
def add_expense_pro(request):
    if request.method != "POST":
        return redirect("expenses_list")

    title = (request.POST.get("title") or "").strip()
    amount_raw = (request.POST.get("amount") or "").strip()
    payer_id = request.POST.get("payer")
    split_type = request.POST.get("split_type")
    participant_ids = request.POST.getlist("participants")

    hh = request.user.profile.active_household
    if not hh:
        messages.error(request, "Please select an active household first.")
        return redirect("household_settings")

    if not title:
        messages.error(request, "Please enter a title for the expense.")
        return redirect("expenses_list")

    if not amount_raw or not participant_ids:
        messages.error(
            request, "Please provide an amount and select at least one person."
        )
        return redirect("expenses_list")

    try:
        total_amount = Decimal(amount_raw).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        messages.error(request, "Please enter a valid total amount.")
        return redirect("expenses_list")

    if total_amount <= 0:
        messages.error(request, "Total amount must be greater than 0.")
        return redirect("expenses_list")

    try:
        payer = CustomUser.objects.get(id=payer_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "Selected payer was not found.")
        return redirect("expenses_list")

    # Make sure payer belongs to active household
    if not HouseholdMember.objects.filter(user=payer, household=hh).exists():
        messages.error(request, "Selected payer is not part of the active household.")
        return redirect("expenses_list")

    participants = list(
        CustomUser.objects.filter(
            id__in=participant_ids,
            memberships__household=hh,
        ).distinct()
    )

    if len(participants) != len(participant_ids):
        messages.error(request, "One or more selected participants are invalid.")
        return redirect("expenses_list")

    if split_type not in ["EQUAL", "PERCENT", "AMOUNT"]:
        messages.error(request, "Invalid split type.")
        return redirect("expenses_list")

    expense = Expense.objects.create(
        title=title,
        amount=total_amount,
        payer=payer,
        household=hh,
        split_type=split_type,
        date_spent=timezone.now().date(),
    )

    cent = Decimal("0.01")

    if split_type == "EQUAL":
        num_people = len(participants)
        equal_share = (total_amount / num_people).quantize(cent, rounding=ROUND_HALF_UP)

        splits = []
        running_total = Decimal("0.00")

        for index, user in enumerate(participants):
            share = equal_share
            if index == num_people - 1:
                share = total_amount - running_total
            else:
                running_total += share

            splits.append((user, share))

        for user, share in splits:
            ExpenseSplit.objects.create(
                expense=expense,
                user=user,
                amount_owed=share,
            )

    elif split_type == "PERCENT":
        entered_percentages = []
        percent_total = Decimal("0")

        for user in participants:
            raw_pct = (request.POST.get(f"percent_{user.id}") or "0").strip()
            try:
                pct = Decimal(raw_pct)
            except (InvalidOperation, TypeError):
                expense.delete()
                messages.error(
                    request, f"Please enter a valid percentage for {user.username}."
                )
                return redirect("expenses_list")

            if pct < 0:
                expense.delete()
                messages.error(request, "Percentages cannot be negative.")
                return redirect("expenses_list")

            entered_percentages.append((user, pct))
            percent_total += pct

        if percent_total != Decimal("100"):
            expense.delete()
            messages.error(request, "Percentages must add up to exactly 100.")
            return redirect("expenses_list")

        running_total = Decimal("0.00")

        for index, (user, pct) in enumerate(entered_percentages):
            share = ((pct / Decimal("100")) * total_amount).quantize(
                cent, rounding=ROUND_HALF_UP
            )

            if index == len(entered_percentages) - 1:
                share = total_amount - running_total
            else:
                running_total += share

            ExpenseSplit.objects.create(
                expense=expense,
                user=user,
                amount_owed=share,
            )

    elif split_type == "AMOUNT":
        entered_amounts = []
        amount_total = Decimal("0.00")

        for user in participants:
            raw_amount = (request.POST.get(f"amount_{user.id}") or "0").strip()
            try:
                split_amount = Decimal(raw_amount).quantize(cent)
            except (InvalidOperation, TypeError):
                expense.delete()
                messages.error(
                    request, f"Please enter a valid amount for {user.username}."
                )
                return redirect("expenses_list")

            if split_amount < 0:
                expense.delete()
                messages.error(request, "Split amounts cannot be negative.")
                return redirect("expenses_list")

            entered_amounts.append((user, split_amount))
            amount_total += split_amount

        if amount_total != total_amount:
            expense.delete()
            messages.error(
                request,
                f"Split amounts must add up to ${total_amount:.2f}. "
                f"Current total is ${amount_total:.2f}.",
            )
            return redirect("expenses_list")

        for user, share in entered_amounts:
            ExpenseSplit.objects.create(
                expense=expense,
                user=user,
                amount_owed=share,
            )

    # Log Activity
    ActivityLog.objects.create(
        user=payer,
        household=hh,
        action="EXPENSE_ADDED",
        details=f"Added expense '{title}' for ${total_amount}.",
    )

    messages.success(request, f"Expense '{title}' added and split successfully!")
    return redirect("expenses_list")


@login_required
@transaction.atomic
def settle_split_view(request, split_id):
    active_hh = request.user.profile.active_household
    referer = request.META.get("HTTP_REFERER", "dashboard")

    if not active_hh:
        messages.error(request, "Please set an active household first.")
        return redirect(referer)

    split = (
        ExpenseSplit.objects.filter(id=split_id, expense__household=active_hh)
        .select_related("expense", "user", "expense__payer")
        .first()
    )

    if not split:
        messages.error(request, "Split not found.")
        return redirect(referer)

    if split.is_settled:
        messages.info(request, "This payment is already settled.")
        return redirect(referer)

    # Only payer or payee can settle
    if request.user != split.user and request.user != split.expense.payer:
        messages.error(request, "You do not have permission to settle this split.")
        return redirect(referer)

    split.is_settled = True
    split.settled_at = timezone.now()
    split.settled_by = request.user
    split.save()

    ActivityLog.objects.create(
        user=request.user,
        household=active_hh,
        action="PAYMENT_SETTLED",
        details=(
            f"Settled ${split.amount_owed} for '{split.expense.title}' "
            f"({split.user.username} with {split.expense.payer.username})"
        ),
    )

    messages.success(request, f"Payment of ${split.amount_owed} settled!")
    return redirect(referer)


@login_required
def add_expense(request):
    if request.method == "POST":
        title = request.POST.get("title")
        amount = request.POST.get("amount")
        hh = request.user.profile.active_household

        if hh and title and amount:
            Expense.objects.create(
                title=title, amount=amount, payer=request.user, household=hh
            )
            messages.success(request, f"Added ${amount} for {title}!")
    return redirect("dashboard")


@login_required
def expense_history_view(request):
    profile = request.user.profile
    active_household = profile.active_household

    if not active_household:
        messages.warning(request, "Please select a household to see expenses.")
        return redirect("household_settings")

    all_expenses = (
        Expense.objects.filter(household=active_household)
        .select_related("payer")
        .order_by("-date_spent", "-created_at")
    )

    return render(
        request,
        "accounts/expense_history.html",
        {
            "expenses": all_expenses,
            "active_household": active_household,
        },
    )


@login_required
@transaction.atomic
def delete_expense_pro(request, expense_id):
    if request.method != "POST":
        return redirect("expenses_list")

    profile = request.user.profile
    active_hh = profile.active_household
    referer = request.META.get("HTTP_REFERER", "expenses_list")

    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect(referer)

    expense = Expense.objects.filter(id=expense_id, household=active_hh).first()

    if not expense:
        messages.error(request, "Expense not found.")
        return redirect(referer)

    if expense.payer != request.user:
        messages.error(
            request,
            "You do not have permission to delete this expense. "
            "Only the payer can delete it.",
        )
        return redirect(referer)

    title = expense.title
    amount = expense.amount

    ActivityLog.objects.create(
        user=request.user,
        household=active_hh,
        action="EXPENSE_DELETED",
        details=(
            f"Deleted expense '{title}' for ${amount}. " "All associated debts removed."
        ),
    )

    expense.delete()

    messages.success(request, f"Expense '{title}' deleted successfully.")
    return redirect(referer)


@login_required
@transaction.atomic
def edit_expense_pro(request, expense_id):
    referer = request.META.get("HTTP_REFERER", "expenses_list")
    active_hh = request.user.profile.active_household

    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect(referer)

    expense = Expense.objects.filter(id=expense_id, household=active_hh).first()
    if not expense:
        messages.error(request, "Expense not found.")
        return redirect(referer)

    if expense.payer != request.user:
        messages.error(request, "Only the payer can edit this expense.")
        return redirect(referer)

    if request.method != "POST":
        return redirect(referer)

    title = (request.POST.get("title") or "").strip()
    amount_raw = (request.POST.get("amount") or "").strip()
    split_type = request.POST.get("split_type")
    participant_ids = request.POST.getlist("participants")

    if not title or not amount_raw or not participant_ids:
        messages.error(request, "Title, amount, and participants are required.")
        return redirect(referer)

    try:
        total_amount = Decimal(amount_raw).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        messages.error(request, "Invalid amount.")
        return redirect(referer)

    old_title = expense.title
    old_amount = expense.amount
    expense.title = title
    expense.amount = total_amount
    expense.split_type = split_type
    expense.save()

    expense.splits.all().delete()

    participants = CustomUser.objects.filter(
        id__in=participant_ids, memberships__household=active_hh
    ).distinct()
    cent = Decimal("0.01")

    if split_type == "EQUAL":
        num_people = len(participants)
        equal_share = (total_amount / num_people).quantize(cent, rounding=ROUND_HALF_UP)
        running_total = Decimal("0.00")
        for index, user in enumerate(participants):
            share = (
                equal_share if index < num_people - 1 else total_amount - running_total
            )
            running_total += share
            ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=share)

    elif split_type == "PERCENT":
        running_total = Decimal("0.00")
        for index, user in enumerate(participants):
            pct = Decimal(request.POST.get(f"percent_{user.id}") or "0")
            share = ((pct / Decimal("100")) * total_amount).quantize(
                cent, rounding=ROUND_HALF_UP
            )
            if index == len(participants) - 1:
                share = total_amount - running_total
            running_total += share
            ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=share)

    elif split_type == "AMOUNT":
        entered_amounts = []
        amount_total = Decimal("0.00")

        for user in participants:
            raw_amount = (request.POST.get(f"amount_{user.id}") or "0").strip()
            try:
                split_amount = Decimal(raw_amount).quantize(cent)
            except (InvalidOperation, TypeError):
                messages.error(
                    request, f"Please enter a valid amount for {user.username}."
                )
                return redirect(referer)

            if split_amount < 0:
                messages.error(request, "Split amounts cannot be negative.")
                return redirect(referer)

            entered_amounts.append((user, split_amount))
            amount_total += split_amount

        if amount_total != total_amount:
            messages.error(
                request,
                f"Split amounts must add up to ${total_amount:.2f}. "
                f"Current total is ${amount_total:.2f}.",
            )
            return redirect(referer)

        for user, share in entered_amounts:
            ExpenseSplit.objects.create(
                expense=expense,
                user=user,
                amount_owed=share,
            )

    ActivityLog.objects.create(
        user=request.user,
        household=active_hh,
        action="EXPENSE_EDITED",
        details=(
            f"Edited expense '{title}'. (Was: '{old_title}' for "
            f"${old_amount} -> Now: ${total_amount})"
        ),
    )

    messages.success(request, f"Expense '{title}' updated successfully.")
    return redirect(referer)
