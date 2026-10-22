from django.urls import path
from .views import OrderListCreateView , OrderDetailView , add_order_item 


urlpatterns = [
    path("orders/", OrderListCreateView.as_view(), name="order-list-create"),
    path("orders/<int:pk>/",OrderDetailView.as_view(),name="order-detail",),
    path("orders/<int:pk>/items/",add_order_item,name="add-order-item", ),
]