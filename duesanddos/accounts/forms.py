from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import PasswordChangeForm
from .models import CustomUser, Profile


class RegisterForm(forms.Form):
    username = forms.CharField(max_length=150)
    firstName = forms.CharField(label="First Name")
    lastName = forms.CharField(label="Last Name")
    email = forms.EmailField(widget=forms.EmailInput())
    password = forms.CharField(widget=forms.PasswordInput())
    confirmPassword = forms.CharField(
        widget=forms.PasswordInput(), label="Confirm Password"
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        first_name = cleaned_data.get("firstName")
        last_name = cleaned_data.get("lastName")
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirmPassword")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirmPassword", "Passwords do not match")

        if password:
            temp_user = CustomUser(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

            try:
                validate_password(password, user=temp_user)
            except ValidationError as e:
                self.add_error("password", e)

        return cleaned_data


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["username", "first_name", "last_name", "email", "phone_number"]
        labels = {
            "phone_number": "Phone Number",
        }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["avatar", "bio", "theme", "default_calendar_view"]
        widgets = {
            "theme": forms.Select(attrs={"class": "input-field"}),
            "default_calendar_view": forms.Select(attrs={"class": "input-field"}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    pass
