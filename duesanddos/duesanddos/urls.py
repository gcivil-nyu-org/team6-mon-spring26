from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "accounts/index.html")


urlpatterns = [
    path("", home_redirect, name="home"),
    path("admin/", admin.site.urls),
    # Accounts app routes
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("households.urls")),
    path("accounts/", include("expenses.urls")),
    path("accounts/", include("activities.urls")),
    path("activities/", include("activities.urls")),
    path("accounts/", include("chores.urls")),
    path("accounts/", include("chat.urls")),
    # Allauth routes (e.g., google/login/, etc.)
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
