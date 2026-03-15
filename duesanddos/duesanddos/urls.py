from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


from django.http import HttpResponse

def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    path("healthcheck/", health_check),
    path("", home_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
