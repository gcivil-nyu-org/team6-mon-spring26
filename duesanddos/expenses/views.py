from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator

from accounts.models import CustomUser
from activities.models import ActivityLog
from .models import Expense, ExpenseSplit, Settlement


@login_required
def expenses_list_view(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        return redirect("household_settings")

    selected_month = request.GET.get("filter_month")
    selected_payer = request.GET.get("filter_payer")
    expenses = (
        active_hh.expenses.all()
        .select_related("payer")
        .prefetch_related("splits", "splits__user")
    )

    if selected_month:
        try:
            year, month = selected_month.split("-")
            expenses = expenses.filter(date_spent__year=year, date_spent__month=month)
        except ValueError:
            pass

    if selected_payer:
        expenses = expenses.filter(payer_id=selected_payer)

    expenses = expenses.order_by("-date_spent")
    members = active_hh.members.filter(user__is_deactivated=False).select_related(
        "user"
    )
    all_members = active_hh.members.select_related(
        "user"
    )  # For summary calculations including deactivated
    summary = []
    you_are_owed = 0.0
    you_owe = 0.0

    for member in all_members:
        if member.user == request.user:
            continue
        they_owed_q = (
            ExpenseSplit.objects.filter(
                expense__payer=request.user,
                user=member.user,
                is_settled=False,
                expense__household=active_hh,
            ).aggregate(Sum("amount_owed"))["amount_owed__sum"]
            or 0
        )

        you_owed_q = (
            ExpenseSplit.objects.filter(
                expense__payer=member.user,
                user=request.user,
                is_settled=False,
                expense__household=active_hh,
            ).aggregate(Sum("amount_owed"))["amount_owed__sum"]
            or 0
        )

        they_owe_you = float(they_owed_q)
        you_owe_them = float(you_owed_q)
        you_are_owed += they_owe_you
        you_owe += you_owe_them
        net_with_person = they_owe_you - you_owe_them

        if abs(net_with_person) > 0.01:
            label = (
                f"{member.user.username} OWES YOU"
                if net_with_person > 0
                else f"YOU OWE {member.user.username}"
            )
            summary.append(
                {
                    "id": member.user.id,
                    "username": member.user.username,
                    "balance": abs(net_with_person),
                    "is_positive": net_with_person > 0,
                    "is_negative": net_with_person < 0,
                    "label": label,
                }
            )

    completed_settlements_qs = (
        Settlement.objects.filter(household=active_hh)
        .filter(Q(status="CONFIRMED") | Q(status="DELETE_PENDING"))
        .order_by("-confirmed_at")
    )

    # 1. Paginate Expense History
    expenses_page_num = request.GET.get("expenses_page", 1)
    expenses_paginator = Paginator(expenses, 10)
    expenses_page_obj = expenses_paginator.get_page(expenses_page_num)

    # 2. Paginate Settlement History
    settlements_page_num = request.GET.get("settlements_page", 1)
    settlements_paginator = Paginator(completed_settlements_qs, 10)
    settlements_page_obj = settlements_paginator.get_page(settlements_page_num)

    # 3. Paginate Household Ledger (summary)
    ledger_page_num = request.GET.get("ledger_page", 1)
    ledger_paginator = Paginator(summary, 10)
    ledger_page_obj = ledger_paginator.get_page(ledger_page_num)

    pending_incoming = Settlement.objects.filter(
        receiver=request.user, household=active_hh, status="PENDING"
    )

    return render(
        request,
        "accounts/expenses.html",
        {
            "expenses": expenses_page_obj,
            "summary": ledger_page_obj,
            "completed_settlements": settlements_page_obj,
            "members": members,
            "active_household": active_hh,
            "you_are_owed": you_are_owed,
            "you_owe": you_owe,
            "pending_incoming": pending_incoming,
            "selected_month": selected_month,
            "selected_payer": selected_payer,
        },
    )


@login_required
@transaction.atomic
def request_settlement(request):
    if request.method == "POST":
        receiver_id = request.POST.get("receiver")
        try:
            amount = Decimal(request.POST.get("amount", "0"))
            hh = request.user.profile.active_household
            if amount <= 0 or not receiver_id:
                messages.error(request, "Invalid amount or recipient.")
                return redirect("expenses_list")
            if amount >= Decimal("1000000000"):
                messages.error(
                    request, "Amount is too large. Max allowed is $999,999,999.99"
                )
                return redirect("expenses_list")
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Please enter a valid amount (numbers only).")
            return redirect("expenses_list")
        receiver = CustomUser.objects.get(id=receiver_id)
        Settlement.objects.create(
            payer=request.user,
            receiver=receiver,
            household=hh,
            amount=amount,
            status="PENDING",
        )
        ActivityLog.objects.create(
            user=request.user,
            household=hh,
            action="PAYMENT_SETTLED",
            details=f"Submitted settlement of ${amount} to {receiver.username}.",
        )
        messages.success(request, f"Settlement request for ${amount} sent!")
    return redirect("expenses_list")


@login_required
@transaction.atomic
def confirm_settlement(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id, receiver=request.user)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "reject":
            settlement.delete()
            messages.warning(request, "Settlement request rejected.")
            return redirect("expenses_list")
        settlement.status = "CONFIRMED"
        settlement.confirmed_at = timezone.now()
        settlement.save()
        splits = ExpenseSplit.objects.filter(
            user=settlement.payer,
            expense__payer=request.user,
            is_settled=False,
            expense__household=settlement.household,
        ).order_by("expense__date_spent")
        remaining_amt = float(settlement.amount)
        for s in splits:
            if remaining_amt <= 0:
                break
            settlement.related_splits.add(s)
            owed = float(s.amount_owed)
            if owed <= (remaining_amt + 0.01):
                remaining_amt -= owed
                s.is_settled = True
                s.save()
            else:
                s.amount_owed = Decimal(owed - remaining_amt).quantize(Decimal("0.01"))
                remaining_amt = 0
                s.save()
        messages.success(request, "Payment confirmed!")
    return redirect("expenses_list")


@login_required
def request_delete_settlement(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id)
    if request.user == settlement.payer or request.user == settlement.receiver:
        settlement.status = "DELETE_PENDING"
        settlement.save()
        messages.info(request, "Deletion request sent.")
    return redirect("expenses_list")


@login_required
@transaction.atomic
def approve_delete_settlement(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id)
    if request.user != settlement.receiver:
        messages.error(
            request, "Only the payment recipient can approve this void request."
        )
        return redirect("expenses_list")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            new_exp = Expense.objects.create(
                title=f"Voided Pmt #{settlement.id}",
                amount=settlement.amount,
                payer=settlement.receiver,
                household=settlement.household,
                date_spent=timezone.now().date(),
            )
            ExpenseSplit.objects.create(
                expense=new_exp,
                user=settlement.payer,
                amount_owed=settlement.amount,
                is_settled=False,
            )
            settlement.delete()
            messages.success(request, "Settlement voided. Balance restored.")
        elif action == "reject":
            settlement.status = "CONFIRMED"
            settlement.save()
            messages.warning(request, "Deletion request rejected.")
    return redirect("expenses_list")


@login_required
@transaction.atomic
def add_expense_pro(request, expense_id=None):
    hh = request.user.profile.active_household
    if not hh:
        messages.error(request, "Please select an active household first.")
        return redirect("expenses_list")

    expense = None
    if expense_id:
        expense = Expense.objects.filter(id=expense_id, household=hh).first()
        if not expense:
            messages.error(request, "Expense not found.")
            return redirect("expenses_list")
        if expense.payer != request.user:
            messages.error(request, "Only the payer can edit this expense.")
            return redirect("expenses_list")
        if expense.splits.filter(is_settled=True).exists():
            messages.error(
                request,
                "Cannot edit an expense that has already been "
                "partially or fully settled. "
                "Please void the settlements first.",
            )
            return redirect("expenses_list")

    if request.method != "POST":
        return redirect("expenses_list")

    title = (request.POST.get("title") or "").strip()
    amount_raw = (request.POST.get("amount") or "").strip()
    p_ids = request.POST.getlist("participants")

    if not title:
        messages.error(request, "Please enter a title for the expense.")
        messages.error(request, "Title, amount, and participants are required.")
        return redirect("expenses_list")

    if not amount_raw or (not p_ids and title != "Legacy"):
        messages.error(
            request, "Please provide an amount and select at least one person."
        )
        messages.error(request, "Title, amount, and participants are required.")
        return redirect("expenses_list")

    try:
        total_amount = Decimal(amount_raw).quantize(Decimal("0.01"))
        if total_amount <= 0:
            messages.error(request, "Total amount must be greater than 0.")
            return redirect("expenses_list")
        if total_amount >= Decimal("1000000000"):
            messages.error(
                request, "Amount is too large. Max allowed is $999,999,999.99"
            )
            return redirect("expenses_list")
    except (InvalidOperation, TypeError, ValueError):
        messages.error(request, "Please enter a valid total amount (numbers only).")
        return redirect("expenses_list")

    payer_id = request.POST.get("payer")
    if payer_id:
        try:
            payer = CustomUser.objects.get(id=payer_id, is_deactivated=False)
        except (CustomUser.DoesNotExist, ValueError):
            messages.error(request, "Selected payer was not found.")
            return redirect("expenses_list")
    else:
        payer = expense.payer if expense else request.user

    if not hh.members.filter(user=payer).exists():
        messages.error(request, "Selected payer is not part of the active household.")
        return redirect("expenses_list")

    split_type = request.POST.get("split_type") or "EQUAL"
    if split_type not in ["EQUAL", "PERCENT", "AMOUNT"]:
        messages.error(request, "Invalid split type.")
        return redirect("expenses_list")

    if not p_ids:
        participants = [request.user]
    else:
        participants = list(CustomUser.objects.filter(id__in=p_ids))
        hh_user_ids = list(hh.members.values_list("user_id", flat=True))
        if (
            any(p.id not in hh_user_ids for p in participants)
            or any(p.is_deactivated for p in participants)
            or len(participants) != len(p_ids)
        ):
            messages.error(
                request, "One or more selected participants are invalid or deactivated."
            )
            return redirect("expenses_list")

    split_data = []
    cent = Decimal("0.01")

    if split_type == "PERCENT":
        total_pct = Decimal("0")
        for u in participants:
            val = request.POST.get(f"percent_{u.id}") or request.POST.get(
                f"split_value_{u.id}", "0"
            )
            try:
                p = Decimal(val)
                if p < 0:
                    messages.error(request, "Percentages cannot be negative.")
                    return redirect("expenses_list")
                total_pct += p
                split_data.append(
                    (u, (total_amount * (p / 100)).quantize(cent, ROUND_HALF_UP))
                )
            except (InvalidOperation, TypeError):
                messages.error(
                    request, f"Please enter a valid percentage for {u.username}."
                )
                return redirect("expenses_list")
        if total_pct != 100:
            messages.error(request, "Percentages must add up to exactly 100.")
            return redirect("expenses_list")

    elif split_type == "AMOUNT":
        total_sum = Decimal("0")
        for u in participants:
            val = request.POST.get(f"amount_{u.id}") or request.POST.get(
                f"split_value_{u.id}", "0"
            )
            try:
                a = Decimal(val).quantize(cent)
                if a < 0:
                    messages.error(request, "Split amounts cannot be negative.")
                    return redirect("expenses_list")
                total_sum += a
                split_data.append((u, a))
            except (InvalidOperation, TypeError):
                messages.error(
                    request, f"Please enter a valid amount for {u.username}."
                )
                return redirect("expenses_list")
        if total_sum != total_amount:
            messages.error(
                request,
                f"Split amounts must add up to ${total_amount}. "
                f"Current total is ${total_sum}.",
            )
            return redirect("expenses_list")

    else:
        num = len(participants)
        share = (total_amount / num).quantize(cent, ROUND_HALF_UP)
        running = Decimal("0.00")
        for i, u in enumerate(participants):
            s = share if i < num - 1 else total_amount - running
            running += s
            split_data.append((u, s))

    is_new = expense is None
    old_amount = None
    if not is_new:
        old_amount = expense.amount

    if is_new:
        expense = Expense.objects.create(
            title=title,
            amount=total_amount,
            payer=payer,
            household=hh,
            split_type=split_type,
            date_spent=timezone.now().date(),
        )
    else:
        expense.title, expense.amount, expense.payer, expense.split_type = (
            title,
            total_amount,
            payer,
            split_type,
        )
        expense.save()
        expense.splits.all().delete()

    for u, amt in split_data:
        ExpenseSplit.objects.create(expense=expense, user=u, amount_owed=amt)

    if is_new:
        log_details = f"Added expense '{title}' of ${total_amount}."
    else:
        if old_amount != total_amount:
            log_details = (
                f"Updated expense '{title}': amount changed "
                f"from ${old_amount} to ${total_amount}."
            )
        else:
            log_details = f"Updated details for expense '{title}' (${total_amount})."

    ActivityLog.objects.create(
        user=request.user,
        household=hh,
        action="EXPENSE_ADDED" if is_new else "EXPENSE_EDITED",
        details=log_details,
    )

    messages.success(
        request, "Updated successfully" if not is_new else "Expense added!"
    )

    if (
        request.POST.get("next") == "dashboard"
        or title == "Legacy"
        or "dashboard" in request.path
    ):
        return redirect("dashboard")
    return redirect("expenses_list")


@login_required
def delete_expense_pro(request, expense_id):
    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please select an active household first.")
        return redirect("expenses_list")

    expense = Expense.objects.filter(id=expense_id, household=active_hh).first()
    if not expense:
        messages.error(request, "Expense not found.")
        return redirect("expenses_list")

    if request.method == "POST":
        if expense.payer != request.user:
            messages.error(request, "Only the payer can delete it.")
        else:
            expense.delete()
            messages.success(request, "Expense deleted successfully.")
    return redirect("expenses_list")


@login_required
def edit_expense_pro(request, expense_id):
    return add_expense_pro(request, expense_id=expense_id)


@login_required
def settle_split(request, split_id):
    active_hh = request.user.profile.active_household
    if not active_hh:
        messages.error(request, "Please set an active household first.")
        return redirect("expenses_list")

    split = ExpenseSplit.objects.filter(id=split_id).first()
    if not split:
        messages.error(request, "Split not found.")
        return redirect("expenses_list")

    if split.is_settled:
        messages.error(request, "This payment is already settled.")
    elif split.user != request.user:
        messages.error(request, "You do not have permission to settle this split.")
    else:
        split.is_settled = True
        split.save()
        messages.success(request, "settled!")
    return redirect("expenses_list")
