from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        """Standard login redirect"""
        return reverse('dashboard')


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        """Redirect to dashboard after an existing user connects a social account"""
        return reverse('dashboard')

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Always return False so new social users are redirected to the signup form.
        We intercept this via SOCIALACCOUNT_AUTO_SIGNUP=False in settings,
        but explicitly overriding ensures it behaves.
        """
        return False
