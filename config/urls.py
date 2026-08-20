"""Root URL configuration.

Each domain app owns its own urls.py; this module only mounts them under /api/
and exposes the schema + Swagger UI.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

api_patterns = [
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.properties.urls")),
    path("", include("apps.members.urls")),
    path("", include("apps.contracts.urls")),
    # Further domain routes are added here as each app lands.
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
    # OpenAPI schema + interactive docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
