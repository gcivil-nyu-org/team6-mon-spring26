from django.urls import path
from . import views

urlpatterns = [
    path(
        "household-settings/", views.household_settings_view, name="household_settings"
    ),
]
