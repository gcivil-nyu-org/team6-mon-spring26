from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView
from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils import timezone

from datetime import timedelta
from .models import CustomUser, Profile, Household, HouseholdMember
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

            login(request, user)
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
            else:
                # PRG: flash errors as toasts and redirect so a browser refresh
                # doesn't re-POST — form fields revert to real DB values on GET
                for field, errors in user_form.errors.items():
                    label = (
                        user_form.fields[field].label
                        if field in user_form.fields
                        else field.replace("_", " ").title()
                    )
                    for error in errors:
                        messages.error(request, f"{label}: {error}")
                for field, errors in profile_form.errors.items():
                    label = (
                        profile_form.fields[field].label
                        if field in profile_form.fields
                        else field.replace("_", " ").title()
                    )
                    for error in errors:
                        messages.error(request, f"{label}: {error}")
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


@login_required
def dashboard_view(request):
    return render(request, "accounts/dashboard.html")


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

        # 4. Update Name
        if action == "update_name":
            if is_admin:
                new_name = request.POST.get("name", "").strip()
                if new_name:
                    active_household.name = new_name
                    active_household.save()
                    messages.success(request, "Household name updated.")
            else:
                messages.error(request, "Only Admins can change the household name.")

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
                                    "As the only admin, you must either assign another admin or delete the household instead.",  # noqa: E501
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

    return redirect("edit_profile")
