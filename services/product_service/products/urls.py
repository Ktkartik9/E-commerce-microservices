from django.urls import path
from .views import ProductListCreateView,ProductDetailView,CategoryListCreateView,update_product_stock ,reserve_product_stock

urlpatterns = [
    path("products/",ProductListCreateView.as_view(),name="product-list-create",),
    path("products/<int:pk>/",ProductDetailView.as_view(),name="product-detail",),
    path("categories/",CategoryListCreateView.as_view(),name="category-list-create",),
    path("products/<int:pk>/stock/",update_product_stock,name="product-stock-update",),
    path(
    "products/<int:pk>/reserve-stock/",
    reserve_product_stock,
    name="reserve-product-stock",
),
]