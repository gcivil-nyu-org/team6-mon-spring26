from django.urls import path
from . import views

urlpatterns = [
    path("chores/", views.chores_list_view, name="chores_list"),
    path("chores/add/", views.add_chore_view, name="add_chore"),
    path("chores/calendar/events/", views.chores_calendar_events, name="chores_calendar_events"),
]