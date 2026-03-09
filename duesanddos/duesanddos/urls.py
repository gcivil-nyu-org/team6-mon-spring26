from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")

urlpatterns = [
    path("", home_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)