from django.urls import path
from .views import OrderListCreateView , OrderDetailView , add_order_item , update_order_status  , cancel_order , pay_for_order


urlpatterns = [
    path("orders/", OrderListCreateView.as_view(), name="order-list-create"),
    path("orders/<int:pk>/",OrderDetailView.as_view(),name="order-detail",),
    path("orders/<int:pk>/items/",add_order_item,name="add-order-item", ),
    path("orders/<int:pk>/status/",update_order_status,name="order-status-update",),
    path("orders/<int:pk>/cancel/",cancel_order,name="cancel-order",),
    path("<int:pk>/pay/", pay_for_order, name="pay-for-order"),
]