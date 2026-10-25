import uuid
from itertools import product
from django.db import transaction
from rest_framework import generics, request
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer
from .product_client import get_product , reserve_stock , release_stock 
from .payment_client import process_payment



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
    # 1. Find the order
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 2. Check order status
    if order.status in ["shipped", "delivered", "cancelled"]:
        return Response(
            {
                "error": "Cannot add items to this order in its current status."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Get product ID
    product_id = request.data.get("product_id")

    if not product_id:
        return Response(
            {"error": "Product ID is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return Response(
            {"error": "Product ID must be a valid integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if product_id < 1:
        return Response(
            {"error": "Product ID must be a positive integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4. Get product from Product Service
    product = get_product(product_id)

    if product is None:
        return Response(
            {
                "error": (
                    "Product not found or Product Service is unavailable."
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not product.get("is_active"):
        return Response(
            {"error": "This product is currently unavailable."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 5. Validate quantity
    quantity = request.data.get("quantity", 1)

    if isinstance(quantity, bool):
        return Response(
            {"error": "Quantity must be a positive integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
                "available_stock": product["stock"],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 6. Prevent adding the same product twice to this order
    if OrderItem.objects.filter(
        order=order,
        product_id=product_id,
    ).exists():
        return Response(
            {"error": "This product is already added to the order."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 7. Prepare serializer data
    data = request.data.copy()
    data["product_id"] = product_id
    data["quantity"] = quantity
    data["price"] = product["price"]

    serializer = OrderItemSerializer(data=data)

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 8. Get or generate reservation ID
    reservation_id = request.data.get("reservation_id")

    if not reservation_id:
        reservation_id = str(uuid.uuid4())

    try:
        reservation_id = str(uuid.UUID(str(reservation_id)))
    except (ValueError, TypeError, AttributeError):
        return Response(
            {"error": "Reservation ID must be a valid UUID."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 9. Reserve stock in Product Service
    reservation = reserve_stock(
        product_id,
        quantity,
        reservation_id=reservation_id,
    )

    if not reservation["success"]:
        error_status = reservation.get("status_code", 502)

        if not 400 <= error_status <= 599:
            error_status = status.HTTP_502_BAD_GATEWAY

        return Response(
            {
                "error": reservation.get(
                    "error", "Stock reservation failed."
                ),
                "details": reservation.get("details"),
            },
            status=error_status,
        )

    reservation_data = reservation["data"]

    # 10. Validate reservation response
    if reservation_data.get("product_id") != product_id:
        return Response(
            {
                "error": (
                    "Reservation product does not match "
                    "the requested product."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )

    if reservation_data.get("released") is True:
        return Response(
            {
                "error": "This reservation has already been released.",
                "detail": "Use a new reservation ID for a new attempt.",
            },
            status=status.HTTP_409_CONFLICT,
        )

    if reservation_data.get("reserved_quantity") != quantity:
        return Response(
            {"error": "Unexpected stock reservation response."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # 11. Handle a repeated request using the same reservation ID
    existing_item = OrderItem.objects.filter(
        reservation_id=reservation_id
    ).first()

    if existing_item:
        if (
            existing_item.order_id == order.id
            and existing_item.product_id == product_id
            and existing_item.quantity == quantity
        ):
            return Response(
                OrderItemSerializer(existing_item).data,
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "This reservation has already been used."},
            status=status.HTTP_409_CONFLICT,
        )

    # 12. Create order item and update order total
    try:
        with transaction.atomic():
            order_item = serializer.save(
                order=order,
                reservation_id=reservation_id,
            )

            order.total_amount = sum(
                item.quantity * item.price
                for item in order.items.all()
            )

            order.save(
                update_fields=["total_amount", "updated_at"]
            )

    except Exception:
        # Compensate by releasing the reserved stock
        try:
            release_result = release_stock(
                product_id,
                quantity,
                reservation_id,
            )
        except Exception:
            release_result = None

        if release_result is None:
            return Response(
                {
                    "error": "Order creation failed.",
                    "detail": (
                        "Stock release could not be confirmed. "
                        "Reconciliation may be required."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "error": "Order creation failed.",
                "detail": "Stock release was successful.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 13. Return the created item
    return Response(
        OrderItemSerializer(order_item).data,
        status=status.HTTP_201_CREATED,
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
    # 1. Find the order
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 2. Check whether cancellation is allowed
    if order.status in ["shipped", "delivered"]:
        return Response(
            {"error": "This order cannot be cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Handle repeated cancellation
    if order.status == "cancelled":
        return Response(
            {"message": "Order is already cancelled."},
            status=status.HTTP_200_OK,
        )

    # 4. Release reserved stock for every order item
    items = list(order.items.all())

    for item in items:
        try:
            release_result = release_stock(
                item.product_id,
                item.quantity,
                str(item.reservation_id),
            )
        except Exception:
            release_result = None

        if release_result is None:
            return Response(
                {
                    "error": "Order cancellation could not be completed.",
                    "detail": (
                        "Stock release could not be confirmed. "
                        "The order has not been marked as cancelled."
                    ),
                    "order_id": order.id,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

    # 5. Mark order as cancelled only after stock releases succeed
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




@api_view(["POST"])
def pay_for_order(request, pk):
    # 1. Find the order
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 2. Allow payment only for pending orders
    if order.status == "confirmed":
        return Response(
            {"message": "Order is already confirmed.", "order_id": order.id},
            status=status.HTTP_200_OK,
        )

    if order.status != "pending":
        return Response(
            {
                "error": "Payment is not allowed for this order status.",
                "status": order.status,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Ensure the order contains items
    if not order.items.exists():
        return Response(
            {"error": "Cannot pay for an order without items."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4. Create a stable idempotency key for this order
    payment_key = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"order-flow-payment-{order.id}",
    )

    # 5. Call Payment Service
    payment_result = process_payment(
        order_id=order.id,
        amount=order.total_amount,
        idempotency_key=payment_key,
    )

    if not payment_result["success"]:
        return Response(
            {
                "error": "Payment failed or Payment Service is unavailable.",
                "payment_status_code": payment_result["status_code"],
                "details": payment_result["data"],
                "order_id": order.id,
                "order_status": order.status,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # 6. Confirm the order after successful payment
    order.status = "confirmed"
    order.save(update_fields=["status", "updated_at"])

    return Response(
        {
            "message": "Payment successful. Order confirmed.",
            "order_id": order.id,
            "amount": str(order.total_amount),
            "order_status": order.status,
            "payment": payment_result["data"],
        },
        status=status.HTTP_200_OK,
    )
