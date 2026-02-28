from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
from .forms import RegisterForm
from .models import CustomUser

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

            messages.success(request, "Account created! Please log in.")
            return redirect("register")  # change to your login url name
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})