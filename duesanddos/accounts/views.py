from datetime import datetime, timedelta
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView
from django.db import transaction, models
from django.utils.crypto import get_random_string
from django.utils import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.paginator import Paginator
from .models import (
    CustomUser,
    Profile,
    Household,
    HouseholdMember,
    Expense,
    ExpenseSplit,
    ActivityLog,
)
from .forms import (
    RegisterForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
)


@transaction.atomic
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            first_name = form.cleaned_data["firstName"].strip()
            last_name = form.cleaned_data["lastName"].strip()
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            Profile.objects.get_or_create(user=user)

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Account created! Please log in.")
            return redirect("profile")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        if "save_profile" in request.POST:
            user_form = UserUpdateForm(request.POST, instance=request.user)
            profile_form = ProfileUpdateForm(
                request.POST, request.FILES, instance=profile
            )
            password_form = CustomPasswordChangeForm(request.user)

            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Your profile was updated.")
                return redirect("profile")
            # Re-render the form with errors so tests and users can see them

        elif "change_password" in request.POST:
            user_form = UserUpdateForm(instance=request.user)
            profile_form = ProfileUpdateForm(instance=profile)
            password_form = CustomPasswordChangeForm(request.user, request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password was changed successfully.")
                return redirect("profile")

        else:
            # Fallback: POST received but no recognized action key — initialize forms unbound  # noqa: E501
            user_form = UserUpdateForm(instance=request.user)
            profile_form = ProfileUpdateForm(instance=profile)
            password_form = CustomPasswordChangeForm(request.user)
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
        password_form = CustomPasswordChangeForm(request.user)

    memberships = HouseholdMember.objects.filter(user=request.user).select_related(
        "household"
    )

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "profile": profile,
            "user_form": user_form,
            "profile_form": profile_form,
            "password_form": password_form,
            "memberships": memberships,
        },
    )


def faq_view(request):
    return render(request, "accounts/faq.html")


def terms_view(request):
    return render(request, "accounts/terms.html")


def privacy_view(request):
    return render(request, "accounts/privacy.html")


class ProtectedLogoutView(LoginRequiredMixin, LogoutView):
    template_name = "accounts/logout.html"

    def get(self, request, *args, **kwargs):
        # Allow GET requests to render the template
        return self.render_to_response(self.get_context_data())


@login_required
def household_settings_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        # 1. Switch Household Context
        if action == "switch_household":
            household_id = request.POST.get("household_id")
            if household_id:
                # verify user is a member
                member_link = HouseholdMember.objects.filter(
                    user=request.user, household_id=household_id
                ).first()
                if member_link:
                    profile.active_household = member_link.household
                    profile.save()
                    messages.success(
                        request, f"Switched context to {member_link.household.name}"
                    )
            return redirect("household_settings")

        # 2. Create Household
        elif action == "create_household":
            name = request.POST.get("household_name", "").strip()
            if name:
                new_household = Household.objects.create(name=name)
                HouseholdMember.objects.create(
                    user=request.user, household=new_household, role="Admin"
                )
                profile.active_household = new_household
                profile.save()
                messages.success(request, f"Household '{name}' created successfully!")
            return redirect("household_settings")

        # 3. Join Household
        elif action == "join_household":
            code = request.POST.get("invite_code", "").strip().upper()
            if code:
                household = Household.objects.filter(invite_code=code).first()
                if household:
                    if (
                        household.invite_code_expires
                        and household.invite_code_expires > timezone.now()
                    ):
                        member, created = HouseholdMember.objects.get_or_create(
                            user=request.user,
                            household=household,
                            defaults={"role": "Member"},
                        )
                        if created:
                            profile.active_household = household
                            profile.save()

                            # Log Activity
                            ActivityLog.objects.create(
                                user=request.user,
                                household=household,
                                action="HOUSEHOLD_JOINED",
                                details=(
                                    f"{request.user.username} joined the household."
                                ),
                            )

                            messages.success(
                                request, f"Successfully joined {household.name}!"
                            )
                        else:
                            messages.info(
                                request, "You are already a member of this household."
                            )
                    else:
                        messages.error(request, "This invite code has expired.")
                else:
                    messages.error(request, "Invalid invite code.")
            return redirect("household_settings")

        # Ensure user has an active household for the following actions
        active_household = profile.active_household
        if not active_household:
            messages.error(request, "No active household selected.")
            return redirect("household_settings")

        is_admin = HouseholdMember.objects.filter(
            user=request.user, household=active_household, role="Admin"
        ).exists()

        # 4. Update General Settings
        if action == "update_general":
            if is_admin:
                new_name = request.POST.get("name", "").strip()
                description = request.POST.get("description", "").strip()
                default_rules = request.POST.get("default_rules", "").strip()
                if new_name:
                    active_household.name = new_name
                    active_household.description = description
                    active_household.default_rules = default_rules
                    active_household.save()
                    messages.success(request, "Household settings updated.")
            else:
                messages.error(request, "Only Admins can change household settings.")

        # 5. Generate Invite Code
        elif action == "generate_invite":
            if is_admin:
                active_household.invite_code = get_random_string(10).upper()
                active_household.invite_code_expires = timezone.now() + timedelta(
                    days=7
                )
                active_household.save()
                messages.success(request, "New invite code generated.")
            else:
                messages.error(request, "Only Admins can generate invite codes.")

        # 6. Update Role
        elif action == "update_role":
            if is_admin:
                target_user_id = request.POST.get("user_id")
                new_role = request.POST.get("role")
                if new_role in dict(HouseholdMember.ROLE_CHOICES).keys():
                    member_link = HouseholdMember.objects.filter(
                        user_id=target_user_id, household=active_household
                    ).first()
                    if member_link:
                        # Prevent last admin from demoting themselves
                        if member_link.user == request.user and new_role != "Admin":
                            admin_count = HouseholdMember.objects.filter(
                                household=active_household, role="Admin"
                            ).count()
                            if admin_count <= 1:
                                messages.error(
                                    request,
                                    "You cannot demote yourself as the only admin.",
                                )
                                return redirect("household_settings")
                        member_link.role = new_role
                        member_link.save()
                        messages.success(request, "Role updated successfully.")
            else:
                messages.error(request, "Only Admins can manage roles.")

        # 7. Remove Member / Leave
        elif action == "remove_member":
            target_user_id = request.POST.get("user_id")
            # Can remove if Admin OR if removing themselves (leaving)
            if is_admin or str(request.user.id) == str(target_user_id):
                member_link = HouseholdMember.objects.filter(
                    user_id=target_user_id, household=active_household
                ).first()
                if member_link:
                    # Prevent last admin from leaving without a successor
                    if member_link.user == request.user and member_link.role == "Admin":
                        admin_count = HouseholdMember.objects.filter(
                            household=active_household, role="Admin"
                        ).count()
                        if admin_count <= 1:
                            new_admin_id = request.POST.get("new_admin_id")
                            if new_admin_id:
                                new_admin_link = HouseholdMember.objects.filter(
                                    user_id=new_admin_id, household=active_household
                                ).first()
                                if new_admin_link:
                                    new_admin_link.role = "Admin"
                                    new_admin_link.save()
                                else:
                                    messages.error(
                                        request, "Selected successor not found."
                                    )
                                    return redirect("household_settings")
                            else:
                                messages.error(
                                    request,
                                    "As the only admin, you must either assign another "
                                    "admin or delete the household instead.",  # noqa: E501
                                )
                                return redirect("household_settings")

                    member_link.delete()

                    if str(request.user.id) == str(target_user_id):
                        # Request user left, fall back to another household if available
                        next_membership = HouseholdMember.objects.filter(
                            user=request.user
                        ).first()
                        profile.active_household = (
                            next_membership.household if next_membership else None
                        )
                        profile.save()
                        messages.success(request, "You left the household.")
                    else:
                        messages.success(request, "Member removed.")

                    # Log Activity
                    msg = f"{member_link.user.username} was removed from the household."
                    if str(request.user.id) == str(target_user_id):
                        msg = f"{member_link.user.username} left the household."

                    ActivityLog.objects.create(
                        user=request.user,
                        household=active_household,
                        action="MEMBER_REMOVED",
                        details=msg,
                    )
            else:
                messages.error(request, "Only Admins can remove other members.")

        # 8. Delete Household
        elif action == "delete_household":
            if is_admin:
                active_household.delete()
                # Fall back to another household
                next_membership = HouseholdMember.objects.filter(
                    user=request.user
                ).first()
                profile.active_household = (
                    next_membership.household if next_membership else None
                )
                profile.save()
                messages.success(request, "Household deleted forever.")
                return redirect("dashboard")
            else:
                messages.error(request, "Only Admins can delete the household.")

        return redirect("household_settings")

    # GET Request Processing
    my_memberships = HouseholdMember.objects.filter(user=request.user).select_related(
        "household"
    )
    my_households = [m.household for m in my_memberships]
    active_household = profile.active_household

    # If no active household but user belongs to some, randomly set one
    if not active_household and my_memberships.exists():
        active_household = my_memberships.first().household
        profile.active_household = active_household
        profile.save()

    members = []
    is_admin = False
    active_invite_code = None

    if active_household:
        members = HouseholdMember.objects.filter(
            household=active_household
        ).select_related("user")
        is_admin = HouseholdMember.objects.filter(
            user=request.user, household=active_household, role="Admin"
        ).exists()

        if (
            active_household.invite_code
            and active_household.invite_code_expires
            and active_household.invite_code_expires > timezone.now()
        ):
            active_invite_code = active_household.invite_code

    context = {
        "my_households": my_households,
        "active_household": active_household,
        "members": members,
        "is_admin": is_admin,
        "active_invite_code": active_invite_code,
    }
    return render(request, "accounts/household_settings.html", context)


@login_required
def delete_account_view(request):
    if request.method == "POST":
        confirmation = request.POST.get("confirmation", "")
        user = request.user

        # Determine verification method
        if user.has_usable_password():
            if not user.check_password(confirmation):
                messages.error(request, "Incorrect password. Account deletion aborted.")
                return redirect("profile")
        else:
            if confirmation != "DELETE":
                messages.error(request, "please type as it is - case sensitive")
                return redirect("profile")

        # Proceed with deletion
        with transaction.atomic():
            # Delete connected households
            Household.objects.filter(members__user=user).delete()
            # Delete the user (this cascades to Profile and HouseholdMember)
            user.delete()

        messages.success(request, "Your account has been successfully deleted.")
        return redirect("login")

    return redirect("profile")


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
def dashboard_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    active_hh = profile.active_household

    if not active_hh:
        return render(request, "accounts/dashboard.html", {"no_household": True})

    # 1. Handle Date Filtering
    # Default: First day of current month to Today
    today = timezone.now().date()
    default_start = today.replace(day=1).strftime("%Y-%m-%d")
    default_end = today.strftime("%Y-%m-%d")

    start_date_str = request.GET.get("start_date", default_start)
    end_date_str = request.GET.get("end_date", default_end)

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        start_date = today.replace(day=1)
        end_date = today

    # Filter sources by date range
    expenses = active_hh.expenses.filter(date_spent__range=(start_date, end_date))
    total_spent = sum(e.amount for e in expenses)
    members = active_hh.members.select_related("user")

    summary = []
    user_net = 0.0

    # 2. Filter Outstanding Debts within the time period
    owed_results = (
        ExpenseSplit.objects.filter(
            expense__payer=request.user,
            expense__household=active_hh,
            is_settled=False,
            expense__date_spent__range=(start_date, end_date),
        )
        .exclude(user=request.user)
        .values("user__username")
        .annotate(total=models.Sum("amount_owed"))
    )

    owed_breakdown = [
        {"name": r["user__username"], "amount": float(r["total"])} for r in owed_results
    ]

    owe_results = (
        ExpenseSplit.objects.filter(
            user=request.user,
            expense__household=active_hh,
            is_settled=False,
            expense__date_spent__range=(start_date, end_date),
        )
        .exclude(expense__payer=request.user)
        .values("expense__payer__username")
        .annotate(total=models.Sum("amount_owed"))
    )

    owe_to_breakdown = [
        {"name": r["expense__payer__username"], "amount": float(r["total"])}
        for r in owe_results
    ]

    for member in members:
        paid_in_period = float(
            sum(e.amount for e in expenses if e.payer == member.user)
        )

        to_me = float(
            ExpenseSplit.objects.filter(
                expense__payer=member.user,
                expense__household=active_hh,
                is_settled=False,
                expense__date_spent__range=(start_date, end_date),
            )
            .exclude(user=member.user)
            .aggregate(models.Sum("amount_owed"))["amount_owed__sum"]
            or 0
        )

        by_me = float(
            ExpenseSplit.objects.filter(
                user=member.user,
                expense__household=active_hh,
                is_settled=False,
                expense__date_spent__range=(start_date, end_date),
            )
            .exclude(expense__payer=member.user)
            .aggregate(models.Sum("amount_owed"))["amount_owed__sum"]
            or 0
        )

        net = to_me - by_me

        summary.append(
            {
                "user_id": member.user.id,
                "username": member.user.username,
                "paid": paid_in_period,
                "balance": net,
            }
        )

        if member.user == request.user:
            user_net = net

    context = {
        "active_household": active_hh,
        "you_are_owed": max(0, user_net),
        "you_owe": abs(min(0, user_net)),
        "total_spent": total_spent,
        "owed_breakdown": owed_breakdown,
        "owe_to_breakdown": owe_to_breakdown,
        "summary": summary,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def activity_log_view(request):
    active_hh = request.user.profile.active_household
    if not active_hh:
        return redirect("household_settings")

    # Date Filter Logic (similar to dashboard)
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
            from .models import Expense

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

    # Acceptance Criteria: List of all past expenses, sorted newest first
    # This retrieves every expense ever logged for this house
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

    # Security: Only the payer can delete the expense
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
            f"Deleted expense '{title}' for ${amount}. "
            f"All associated debts removed."
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

    # 1. Update Expense Basic Info
    old_title = expense.title
    old_amount = expense.amount
    expense.title = title
    expense.amount = total_amount
    expense.split_type = split_type
    expense.save()

    # 2. Update Splits (Delete and Recreate)
    # For now, we allow the edit but warn that it might've affected
    # settled records if they existed.
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

    # 3. Log Activity
    ActivityLog.objects.create(
        user=request.user,
        household=active_hh,
        action="EXPENSE_EDITED",
        details=(
            f"Edited expense '{title}'. (Was: '{old_title}' "
            f"for ${old_amount} -> Now: ${total_amount})"
        ),
    )

    messages.success(request, f"Expense '{title}' updated successfully.")
    return redirect(referer)
