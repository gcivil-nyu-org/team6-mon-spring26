from datetime import datetime
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView
from django.db import transaction, models
from django.utils import timezone

from .models import CustomUser, Profile
from households.models import Household, HouseholdMember
from expenses.models import ExpenseSplit
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
        return self.render_to_response(self.get_context_data())


@login_required
def delete_account_view(request):
    if request.method == "POST":
        confirmation = request.POST.get("confirmation", "")
        user = request.user

        if user.has_usable_password():
            if not user.check_password(confirmation):
                messages.error(request, "Incorrect password. Account deletion aborted.")
                return redirect("profile")
        else:
            if confirmation != "DELETE":
                messages.error(request, "please type as it is - case sensitive")
                return redirect("profile")

        with transaction.atomic():
            Household.objects.filter(members__user=user).delete()
            user.delete()

        messages.success(request, "Your account has been successfully deleted.")
        return redirect("login")

    return redirect("profile")


@login_required
def dashboard_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    active_hh = profile.active_household

    if not active_hh:
        return render(request, "accounts/dashboard.html", {"no_household": True})

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

    expenses = active_hh.expenses.filter(date_spent__range=(start_date, end_date))
    total_spent = sum(e.amount for e in expenses)
    members = active_hh.members.select_related("user")

    summary = []
    user_net = 0.0

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
