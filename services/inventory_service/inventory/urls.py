from django.urls import path

from .views import (
    InventoryListCreateView,
    InventoryDetailView,
    reserve_stock,
    release_stock,

)

urlpatterns = [
    path(
        "inventory/",
        InventoryListCreateView.as_view(),
        name="inventory-list-create",
    ),
    path(
        "inventory/<int:product_id>/",
        InventoryDetailView.as_view(),
        name="inventory-detail",
    ),
    path(
        "inventory/<int:product_id>/reserve/",
        reserve_stock,
        name="reserve-stock",
    ),
    path(
    "inventory/<int:product_id>/release/",
    release_stock,
    name="release-stock",
    ),
]