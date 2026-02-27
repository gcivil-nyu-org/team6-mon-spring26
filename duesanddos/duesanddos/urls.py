from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("login/", include("loginpython manage.py runserver.urls")),
    path("admin/", admin.site.urls),
]