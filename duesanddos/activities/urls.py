from django.urls import path
from . import views

urlpatterns = [
    path("activity/", views.activity_log_view, name="activity_log"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("api/calendar-events/", views.calendar_events_api, name="calendar_events_api"),
    path(
        "api/update-view-pref/",
        views.update_calendar_view_pref,
        name="update_calendar_view_pref",
    ),
    path("feed/", views.activity_feed_view, name="activity_feed"),
]
