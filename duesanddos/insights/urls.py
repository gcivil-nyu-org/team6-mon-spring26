from django.urls import path
from .views import insights_view

urlpatterns = [
    path("insights/", insights_view, name="insights"),
]
