from datetime import timedelta
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from django.utils import timezone
from .models import Household, HouseholdMember
from accounts.models import Profile
from activities.models import ActivityLog


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
                                    "admin or delete the household instead.",
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
def switch_household_view(request, household_id):
    profile, created = Profile.objects.get_or_create(user=request.user)

    # Verify user is a member of the target household
    member_link = HouseholdMember.objects.filter(
        user=request.user, household_id=household_id
    ).first()

    if member_link:
        profile.active_household = member_link.household
        profile.save()
        messages.success(request, f"Switched context to {member_link.household.name}")
    else:
        messages.error(request, "You do not have access to this household.")

    return redirect(request.META.get("HTTP_REFERER", "dashboard"))
