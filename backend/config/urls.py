from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    """Cheap liveness probe — also handy for warming Render's free dyno."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", health),
    path("healthz/", health),
    path("django-admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("notifications.urls")),
]
