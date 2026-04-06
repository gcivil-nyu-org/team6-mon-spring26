from django.urls import path
from . import views

urlpatterns = [
    path("activity/", views.activity_log_view, name="activity_log"),
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/calendar-events/', views.calendar_events_api, name='calendar_events_api'),
    path('feed/', views.activity_feed_view, name='activity_feed'),
]
