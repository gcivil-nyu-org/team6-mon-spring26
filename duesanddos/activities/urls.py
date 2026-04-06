from django.urls import path
from . import views

urlpatterns = [
    path("activity/", views.activity_log_view, name="activity_log"),
]
