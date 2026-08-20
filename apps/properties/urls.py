from django.urls import path

from .views import (
    PropertyDetailView,
    PropertyListCreateView,
    UnitCreateView,
    UnitListView,
)

app_name = "properties"

# Mounted at /api/ -- see config/urls.py
urlpatterns = [
    path("properties", PropertyListCreateView.as_view(), name="property-list"),
    path("properties/<int:property_id>", PropertyDetailView.as_view(), name="property-detail"),
    path("properties/<int:property_id>/units", UnitCreateView.as_view(), name="unit-create"),
    path("units", UnitListView.as_view(), name="unit-list"),
]
