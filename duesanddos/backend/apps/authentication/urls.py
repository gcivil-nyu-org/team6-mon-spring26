from django.urls import path
from apps.authentication.views import (
    RegisterView,
    LoginView,
    LogoutView,
    TokenRefreshCookieView,
    ForgotPasswordView,
    ResetPasswordView,
    GoogleLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshCookieView.as_view(), name="auth-token-refresh"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("google/", GoogleLoginView.as_view(), name="auth-google"),
]
