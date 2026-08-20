from django.urls import path

from .views import ContractDetailView, ContractListCreateView

app_name = "contracts"

urlpatterns = [
    path("contracts", ContractListCreateView.as_view(), name="contract-list"),
    path("contracts/<int:contract_id>", ContractDetailView.as_view(), name="contract-detail"),
]
