from django.urls import path

from .views import MemberListCreateView

app_name = "members"

urlpatterns = [
    path("members", MemberListCreateView.as_view(), name="member-list"),
]
