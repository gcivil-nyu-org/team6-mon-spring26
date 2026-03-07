from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile_view, name="edit_profile"),
    path("login/",  auth_views.LoginView.as_view(template_name="accounts/login.html"),  name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", TemplateView.as_view(template_name="accounts/dashboard.html"), name="dashboard"),
]