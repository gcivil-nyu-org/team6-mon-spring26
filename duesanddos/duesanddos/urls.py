from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("login/", include("login.urls")),
    path("register/", include("users.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
]