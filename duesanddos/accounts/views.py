from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.db import transaction
from .models import CustomUser, Profile
from .forms import RegisterForm, UserUpdateForm, ProfileUpdateForm, CustomPasswordChangeForm

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
    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def edit_profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        if "save_profile" in request.POST:
            user_form = UserUpdateForm(request.POST, instance=request.user)
            profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
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

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )