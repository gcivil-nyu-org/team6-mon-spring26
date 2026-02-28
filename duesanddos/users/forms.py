from django import forms

class RegisterForm(forms.Form):
    identifier = forms.CharField(label="Email or Phone")
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)