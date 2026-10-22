from itertools import product

from rest_framework import generics, request
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer
from .product_client import get_product , reserve_stock


class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        if order.status == "cancelled":
            return Response(
                {"error": "Cannot update a cancelled order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        order = self.get_object()

        if order.status in ["shipped", "delivered"]:
            return Response(
            {"error": "Cannot delete a shipped or delivered order."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        return super().destroy(request, *args, **kwargs)


@api_view(["POST"])
def add_order_item(request, pk):

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    product_id = request.data.get("product_id")

    if not product_id:
        return Response(
            {"error": "Product ID is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product = get_product(product_id)

    if product is None:
        return Response(
            {"error": "Product not found or Product Service is unavailable."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not product.get("is_active"):
        return Response(
        {"error": "This product is currently unavailable."},
        status=status.HTTP_400_BAD_REQUEST,
    )

    quantity = request.data.get("quantity", 1)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response(
        {"error": "Quantity must be a valid integer."},
        status=status.HTTP_400_BAD_REQUEST,
    )

    if quantity < 1:
        return Response(
        {"error": "Quantity must be at least 1."},
        status=status.HTTP_400_BAD_REQUEST,
    )

    if quantity > product["stock"]:
        return Response(
        {
            "error": "Insufficient stock.",
            "available_stock":product["stock"],
        },
        status=status.HTTP_400_BAD_REQUEST,
    )

    if order.status in ["shipped", "delivered"]:
        return Response(
        {"error": "Cannot add items to a shipped or delivered order."},
        status=status.HTTP_400_BAD_REQUEST,
    )

    product_id = request.data.get("product_id")

    if OrderItem.objects.filter(
        order=order,
        product_id=product_id,
        ).exists(): 
        return Response(
        {"error": "This product is already added to the order."},
        status=status.HTTP_400_BAD_REQUEST,
    )
    data = request.data.copy()
    data["price"] = product["price"]

    serializer = OrderItemSerializer(data=data)
    
    

    if serializer.is_valid():
        reservation = reserve_stock(product_id, quantity)

        if reservation is None:
            return Response(
                {
                    "error": "Could not reserve product stock.",
                    "detail": "Product Service rejected the request or is unavailable.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reservation.get("reserved_quantity") != quantity:
            return Response(
        {
            "error": "Unexpected stock reservation response.",
        },
        status=status.HTTP_502_BAD_GATEWAY,
        )
        order_item = serializer.save(order=order)

        order.total_amount = sum(
            item.quantity * item.price
            for item in order.items.all()
        )

        order.save(update_fields=["total_amount", "updated_at"])

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )




@api_view(["PATCH"])
def update_order_status(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    new_status = request.data.get("status")
    if not new_status:
        return Response(
        {"error": "Status is required."},
        status=status.HTTP_400_BAD_REQUEST,
    )
    allowed_transitions = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["shipped", "cancelled"],
        "shipped": ["delivered"],
        "delivered": [],
        "cancelled": [],
    }

    if new_status not in allowed_transitions[order.status]:
        return Response(
            {
                "error": "Invalid status transition.",
                "current_status": order.status,
                "requested_status": new_status,
                "allowed_statuses": allowed_transitions[order.status],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    valid_statuses = [
        choice[0] for choice in Order.STATUS_CHOICES
    ]

    if new_status not in valid_statuses:
        return Response(
            {
                "error": "Invalid status.",
                "valid_statuses": valid_statuses,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    return Response(
        {
            "message": "Order status updated successfully.",
            "order_id": order.id,
            "status": order.status,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def cancel_order(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if order.status in ["shipped", "delivered"]:
        return Response(
            {"error": "This order cannot be cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if order.status == "cancelled":
        return Response(
            {"message": "Order is already cancelled."},
            status=status.HTTP_200_OK,
        )

    order.status = "cancelled"
    order.save(update_fields=["status", "updated_at"])

    return Response(
        {
            "message": "Order cancelled successfully.",
            "order_id": order.id,
            "status": order.status,
        },
        status=status.HTTP_200_OK,
    )



class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.all().order_by("-created_at")

        order_status = self.request.query_params.get("status")

        if order_status:
            queryset = queryset.filter(status=order_status)

        return queryset



def get_queryset(self):
    queryset = Order.objects.all().order_by("-created_at")

    order_status = self.request.query_params.get("status")
    user_id = self.request.query_params.get("user_id")

    if order_status:
        queryset = queryset.filter(status=order_status)

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    return queryset
