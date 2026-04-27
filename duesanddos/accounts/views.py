from datetime import datetime
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction, models
from django.utils import timezone

from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib.sites.models import Site
from .models import CustomUser, Profile
from households.models import Household, HouseholdMember
from expenses.models import ExpenseSplit
from .forms import (
    RegisterForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
)


def is_google_app_configured():
    from django.conf import settings

    # Check if configured in settings.py (allauth 0.47+)
    google_config = settings.SOCIALACCOUNT_PROVIDERS.get("google", {})
    if "APP" in google_config and google_config["APP"].get("client_id"):
        return True

    # Fallback: check database (SocialApp model)
    site = Site.objects.get_current()
    return SocialApp.objects.filter(provider="google", sites=site).exists()


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if user.is_deactivated:
            # Store user info in session for reactivation
            self.request.session["pending_reactivation_user_id"] = user.id
            return redirect("reactivate_account_confirm")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_app_configured"] = is_google_app_configured()
        return context


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

    return render(
        request,
        "accounts/register.html",
        {
            "form": form,
            "google_app_configured": is_google_app_configured(),
        },
    )


@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    user_form = UserUpdateForm(instance=request.user)
    profile_form = ProfileUpdateForm(instance=profile)
    password_form = CustomPasswordChangeForm(request.user)
    if request.method == "POST":
        # 1. NEW: Handle the Theme/Calendar auto-submit
        if "update_preferences" in request.POST:
            profile_form = ProfileUpdateForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Display preferences updated.")
                return redirect("profile")

        # 2. Handle the main "Save Changes" button
        elif "save_profile" in request.POST:
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

        # 3. Handle Password Change Modal
        elif "change_password" in request.POST:
            user_form = UserUpdateForm(instance=request.user)
            profile_form = ProfileUpdateForm(instance=profile)
            password_form = CustomPasswordChangeForm(request.user, request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password was changed successfully.")
                return redirect("profile")
    memberships = HouseholdMember.objects.filter(user=request.user).select_related(
        "household"
    )
    google_account = SocialAccount.objects.filter(
        user=request.user, provider="google"
    ).first()

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "profile": profile,
            "user_form": user_form,
            "profile_form": profile_form,
            "password_form": password_form,
            "memberships": memberships,
            "google_account": google_account,
            "google_app_configured": is_google_app_configured(),
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
@transaction.atomic
def deactivate_account_view(request):
    if request.method == "POST":
        confirmation = request.POST.get("confirmation", "")
        user = request.user

        if user.has_usable_password():
            if not user.check_password(confirmation):
                messages.error(request, "Incorrect password. Deactivation aborted.")
                return redirect("profile")
        else:
            if confirmation != "DEACTIVATE":
                messages.error(request, "Please type 'DEACTIVATE' to confirm.")
                return redirect("profile")

        user.is_deactivated = True
        user.save(update_fields=["is_deactivated"])

        logout(request)
        messages.success(
            request, "Your account has been deactivated. You have been logged out."
        )
        return redirect("login")

    return redirect("profile")


def reactivate_account_confirm_view(request):
    user_id = request.session.get("pending_reactivation_user_id")
    if not user_id:
        return redirect("login")

    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        user.is_deactivated = False
        user.save(update_fields=["is_deactivated"])

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        del request.session["pending_reactivation_user_id"]

        messages.success(
            request, f"Welcome back, {user.username}! Your account is now active."
        )
        return redirect("dashboard")

    return render(request, "accounts/reactivate_confirm.html", {"user": user})


@login_required
def toggle_theme(request):
    if request.method == "POST":
        profile = request.user.profile
        profile.theme = "dark" if profile.theme == "light" else "light"
        profile.save(update_fields=["theme"])
        return JsonResponse({"theme": profile.theme})
    return JsonResponse({"error": "Invalid request"}, status=400)


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
def disconnect_google_view(request):
    """Remove the Google social account link from the user's account."""
    if request.method == "POST":
        google_account = SocialAccount.objects.filter(
            user=request.user, provider="google"
        ).first()

        if not google_account:
            messages.warning(request, "No Google account is connected.")
            return redirect("profile")

        # Safety: if the user has no usable password they'd be locked out
        if not request.user.has_usable_password():
            messages.error(
                request,
                "Cannot disconnect Google — you have no password set. "
                "Please set a password first so you don't lose access to your account.",
            )
            return redirect("profile")

        google_account.delete()
        messages.success(request, "Your Google account has been disconnected.")

    return redirect("profile")


@login_required
def dashboard_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    # NOTES: Handle form submissions for fridge note and personal to-do updates
    if request.method == "POST":
        if "save_fridge" in request.POST:
            if profile.active_household:
                profile.active_household.fridge_note = request.POST.get(
                    "fridge_note", ""
                )
                profile.active_household.save()
                messages.success(request, "Household Fridge updated!")

        elif "save_todo" in request.POST:
            profile.personal_todo = request.POST.get("personal_todo", "")
            profile.save()
            messages.success(request, "Personal To-Do updated!")

        return redirect("dashboard")

    try:
        active_hh = profile.active_household
    except Household.DoesNotExist:
        active_hh = None
        profile.active_household = None
        profile.save(update_fields=["active_household"])

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

    today = timezone.now().date()
    all_household_chores = active_hh.chores.filter(is_active=True).prefetch_related(
        "assignees", "completions", "skips"
    )

    pending_chores = []
    for chore in all_household_chores:
        if request.user in chore.assignees.all():
            if chore.occurs_on(today):
                completed = chore.completions.filter(occurrence_date=today).exists()
                skipped = chore.skips.filter(occurrence_date=today).exists()

                if not completed and not skipped:
                    pending_chores.append(chore)

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
        "profile": profile,
        "active_household": active_hh,
        "members": members,
        "pending_chores": pending_chores[:5],
        "today_date": today,
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
