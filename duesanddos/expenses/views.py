from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from households.models import HouseholdMember
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
            year, month = selected_month.split('-')
            expenses = expenses.filter(date_spent__year=year, date_spent__month=month)
        except ValueError:
            pass

    if selected_payer:
        expenses = expenses.filter(payer_id=selected_payer)

    expenses = expenses.order_by("-date_spent")
    
    members = active_hh.members.select_related("user")
    summary = []
    you_are_owed = 0.0
    you_owe = 0.0

    for member in members:
        if member.user == request.user:
            continue

        they_owe_you = float(ExpenseSplit.objects.filter(
            expense__payer=request.user,
            user=member.user,
            is_settled=False,
            expense__household=active_hh
        ).aggregate(Sum("amount_owed"))["amount_owed__sum"] or 0)

        you_owe_them = float(ExpenseSplit.objects.filter(
            expense__payer=member.user,
            user=request.user,
            is_settled=False,
            expense__household=active_hh
        ).aggregate(Sum("amount_owed"))["amount_owed__sum"] or 0)

        you_are_owed += they_owe_you
        you_owe += you_owe_them

        net_with_person = they_owe_you - you_owe_them

        if abs(net_with_person) > 0.01:
            summary.append({
                "id": member.user.id,
                "username": member.user.username,
                "balance": abs(net_with_person),
                "is_positive": net_with_person > 0,
                "is_negative": net_with_person < 0,
                "label": f"{member.user.username} OWES YOU" if net_with_person > 0 else f"YOU OWE {member.user.username}"
            })

    completed_settlements = Settlement.objects.filter(
        household=active_hh
    ).filter(
        Q(status='CONFIRMED') | Q(status='DELETE_PENDING')
    ).order_by('-confirmed_at')[:10]

    pending_incoming = Settlement.objects.filter(
        receiver=request.user, 
        household=active_hh, 
        status='PENDING'
    )

    return render(
        request,
        "accounts/expenses.html",
        {
            "expenses": expenses, 
            "members": members, 
            "active_household": active_hh,
            "summary": summary,
            "you_are_owed": you_are_owed,
            "you_owe": you_owe,
            "pending_incoming": pending_incoming,
            "completed_settlements": completed_settlements,
            "selected_month": selected_month, 
            "selected_payer": selected_payer,  
        },
    )

@login_required
@transaction.atomic
def request_settlement(request):
    if request.method == "POST":
        receiver_id = request.POST.get("receiver")
        amount = Decimal(request.POST.get("amount", "0"))
        hh = request.user.profile.active_household

        if amount <= 0 or not receiver_id:
            messages.error(request, "Invalid amount or recipient.")
            return redirect("expenses_list")

        receiver = CustomUser.objects.get(id=receiver_id)
        
        Settlement.objects.create(
            payer=request.user,
            receiver=receiver,
            household=hh,
            amount=amount,
            status='PENDING'
        )

        ActivityLog.objects.create(
            user=request.user,
            household=hh,
            action="PAYMENT_SETTLED",
            details=f"Submitted settlement of ${amount} to {receiver.username}."
        )
        
        messages.success(request, f"Settlement request for ${amount} sent!")
    return redirect("expenses_list")

@login_required
@transaction.atomic
def confirm_settlement(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id, receiver=request.user)
    
    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'reject':
            settlement.delete()
            messages.warning(request, "Settlement request rejected.")
            return redirect("expenses_list")

        settlement.status = 'CONFIRMED'
        settlement.confirmed_at = timezone.now()
        settlement.save()

        # Update Split Balances
        splits = ExpenseSplit.objects.filter(
            user=settlement.payer, 
            expense__payer=request.user, 
            is_settled=False,
            expense__household=settlement.household
        ).order_by('expense__date_spent')

        remaining_amt = float(settlement.amount)
        for s in splits:
            if remaining_amt <= 0: break
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

        messages.success(request, f"Payment confirmed!")
    return redirect("expenses_list")

@login_required
def request_delete_settlement(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id)
    if request.user == settlement.payer or request.user == settlement.receiver:
        settlement.status = 'DELETE_PENDING'
        settlement.save()
        messages.info(request, "Deletion request sent.")
    return redirect('expenses_list')

@login_required
@transaction.atomic
def approve_delete_settlement(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id)
    
    if request.user != settlement.receiver:
        messages.error(request, "Only the payment recipient can approve this void request.")
        return redirect('expenses_list')

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'approve':
            # Create a 'reversal' expense
            new_expense = Expense.objects.create(
                title=f"Voided Pmt #{settlement.id}",
                amount=settlement.amount,
                payer=settlement.receiver, 
                household=settlement.household,
                date_spent=timezone.now().date()
            )
            ExpenseSplit.objects.create(
                expense=new_expense,
                user=settlement.payer, 
                amount_owed=settlement.amount,
                is_settled=False
            )
            settlement.delete()
            messages.success(request, "Settlement voided. Balance restored.")
        elif action == 'reject':
            settlement.status = 'CONFIRMED'
            settlement.save()
            messages.warning(request, "Deletion request rejected.")
            
    return redirect('expenses_list')

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
    if not hh or not title or not amount_raw or not participant_ids:
        messages.error(request, "Check all required fields.")
        return redirect("expenses_list")

    try:
        total_amount = Decimal(amount_raw).quantize(Decimal("0.01"))
        payer = CustomUser.objects.get(id=payer_id)
    except (InvalidOperation, TypeError, CustomUser.DoesNotExist):
        messages.error(request, "Error in data provided.")
        return redirect("expenses_list")

    expense = Expense.objects.create(
        title=title, amount=total_amount, payer=payer,
        household=hh, split_type=split_type, date_spent=timezone.now().date()
    )

    participants = CustomUser.objects.filter(id__in=participant_ids)
    cent = Decimal("0.01")

    if split_type == "EQUAL":
        num = len(participants)
        share = (total_amount / num).quantize(cent, rounding=ROUND_HALF_UP)
        running = Decimal("0.00")
        for i, u in enumerate(participants):
            s = share if i < num - 1 else total_amount - running
            running += s
            ExpenseSplit.objects.create(expense=expense, user=u, amount_owed=s)


    ActivityLog.objects.create(user=payer, household=hh, action="EXPENSE_ADDED", details=f"Added '{title}' for ${total_amount}.")
    messages.success(request, "Expense added!")
    return redirect("expenses_list")

@login_required
@transaction.atomic
def delete_expense_pro(request, expense_id):
    if request.method == "POST":
        active_hh = request.user.profile.active_household
        expense = get_object_or_404(Expense, id=expense_id, household=active_hh)
        if expense.payer == request.user:
            ActivityLog.objects.create(user=request.user, household=active_hh, action="EXPENSE_DELETED", details=f"Deleted {expense.title}")
            expense.delete()
            messages.success(request, "Deleted.")
    return redirect("expenses_list")