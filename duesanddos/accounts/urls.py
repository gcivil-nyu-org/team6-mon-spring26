from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile_view, name="edit_profile"),
    path("login/",  auth_views.LoginView.as_view(template_name="accounts/login.html"),  name="login"),
    path("logout/", views.ProtectedLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
]