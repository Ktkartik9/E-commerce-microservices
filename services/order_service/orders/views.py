from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer


class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


@api_view(["POST"])
def add_order_item(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = OrderItemSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(order=order)
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
