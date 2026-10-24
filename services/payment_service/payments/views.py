from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Payment
from .serializers import PaymentSerializer


@api_view(["POST"])
def process_payment(request):
    order_id = request.data.get("order_id")
    amount = request.data.get("amount")
    idempotency_key = request.data.get("idempotency_key")
    simulate_failure = request.data.get("simulate_failure", False)

    if isinstance(order_id, bool) or not isinstance(order_id, int) or order_id <= 0:
        return Response(
            {"error": "A valid order_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(amount, bool):
        return Response(
            {"error": "Amount must be a positive number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {"error": "Amount must be a valid number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not amount.is_finite() or amount <= 0:
        return Response(
            {"error": "Amount must be a positive number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(simulate_failure, bool):
        return Response(
            {"error": "simulate_failure must be true or false."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from uuid import UUID
        idempotency_key = UUID(str(idempotency_key))
    except (ValueError, TypeError, AttributeError):
        return Response(
            {"error": "A valid idempotency_key is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = Payment.objects.filter(
        idempotency_key=idempotency_key
    ).first()

    if existing:
        if existing.order_id != order_id or existing.amount != amount:
            return Response(
                {"error": "Idempotency key already used with different data."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            PaymentSerializer(existing).data,
            status=status.HTTP_200_OK,
        )

    payment = Payment.objects.create(
        order_id=order_id,
        amount=amount,
        idempotency_key=idempotency_key,
        status="failed" if simulate_failure else "success",
    )

    response_status = (
        status.HTTP_402_PAYMENT_REQUIRED
        if simulate_failure
        else status.HTTP_201_CREATED
    )

    return Response(
        PaymentSerializer(payment).data,
        status=response_status,
    )