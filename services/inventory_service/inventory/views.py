import uuid
from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import Inventory
from .serializers import InventorySerializer
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Inventory, StockReservation


class InventoryListCreateView(generics.ListCreateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [AllowAny]



class InventoryDetailView(generics.RetrieveAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [AllowAny]
    lookup_field = "product_id"



@api_view(["POST"])
def reserve_stock(request, product_id):
    quantity = request.data.get("quantity")
    reservation_id = request.data.get("reservation_id")

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return Response(
            {"error": "Quantity must be a positive integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        reservation_id = uuid.UUID(str(reservation_id))
    except (ValueError, TypeError, AttributeError):
        return Response(
            {"error": "A valid reservation_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        existing = StockReservation.objects.filter(
            reservation_id=reservation_id
        ).first()

        if existing:
            if (
                existing.inventory.product_id != product_id
                or existing.quantity != quantity
            ):
                return Response(
                    {"error": "Reservation ID already used with different data."},
                    status=status.HTTP_409_CONFLICT,
                )

            return Response(
                {
                    "product_id": product_id,
                    "reserved_quantity": existing.quantity,
                    "reservation_id": str(existing.reservation_id),
                    "released": existing.is_released,
                    "message": "Reservation already exists.",
                },
                status=status.HTTP_200_OK,
            )

        updated = Inventory.objects.filter(
            product_id=product_id,
            available_quantity__gte=quantity,
        ).update(
            available_quantity=F("available_quantity") - quantity
        )

        if not updated:
            return Response(
                {"error": "Inventory not found or insufficient stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inventory = Inventory.objects.get(product_id=product_id)

        reservation = StockReservation.objects.create(
            inventory=inventory,
            reservation_id=reservation_id,
            quantity=quantity,
        )

        return Response(
            {
                "product_id": product_id,
                "reserved_quantity": reservation.quantity,
                "remaining_stock": inventory.available_quantity,
                "reservation_id": str(reservation.reservation_id),
                "released": False,
            },
            status=status.HTTP_201_CREATED,
        )



@api_view(["POST"])
def release_stock(request, product_id):
    reservation_id = request.data.get("reservation_id")

    try:
        reservation_id = uuid.UUID(str(reservation_id))
    except (ValueError, TypeError, AttributeError):
        return Response(
            {"error": "A valid reservation_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        try:
            reservation = StockReservation.objects.select_for_update().get(
                reservation_id=reservation_id,
                inventory__product_id=product_id,
            )
        except StockReservation.DoesNotExist:
            return Response(
                {"error": "Reservation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if reservation.is_released:
            return Response(
                {"message": "Stock already released."},
                status=status.HTTP_200_OK,
            )

        Inventory.objects.filter(pk=reservation.inventory_id).update(
            available_quantity=F("available_quantity") + reservation.quantity
        )

        reservation.is_released = True
        reservation.save(update_fields=["is_released"])

        inventory = Inventory.objects.get(pk=reservation.inventory_id)

        return Response(
            {
                "product_id": product_id,
                "released_quantity": reservation.quantity,
                "available_quantity": inventory.available_quantity,
                "reservation_id": str(reservation.reservation_id),
                "released": True,
            },
            status=status.HTTP_200_OK,
        )