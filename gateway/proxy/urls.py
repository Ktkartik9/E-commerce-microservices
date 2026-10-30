
from django.urls import path, re_path
from .views import proxy_request

urlpatterns = [
    # User Service
    path("api/users/", proxy_request, {"service": "users"}),
    re_path(r"^api/users/(?P<path>.+)$", proxy_request, {"service": "users"}),

    # JWT Authentication
    path("api/token/", proxy_request, {"service": "users"}),
    path("api/token/refresh/", proxy_request, {"service": "users"}),

    # Product Service
    path("api/products/", proxy_request, {"service": "products"}),
    re_path(r"^api/products/(?P<path>.+)$", proxy_request, {"service": "products"}),

    # Order Service
    path("api/orders/", proxy_request, {"service": "orders"}),
    re_path(r"^api/orders/(?P<path>.+)$", proxy_request, {"service": "orders"}),

    # Inventory Service
    path("api/inventory/", proxy_request, {"service": "inventory"}),
    re_path(r"^api/inventory/(?P<path>.+)$", proxy_request, {"service": "inventory"}),

    # Payment Service
    path("api/payments/", proxy_request, {"service": "payments"}),
    re_path(r"^api/payments/(?P<path>.+)$", proxy_request, {"service": "payments"}),
]
