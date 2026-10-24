from rest_framework import serializers

from .models import Inventory, StockReservation


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = [
            "id",
            "product_id",
            "available_quantity",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class StockReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockReservation
        fields = [
            "id",
            "inventory",
            "reservation_id",
            "quantity",
            "is_released",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "reservation_id",
            "is_released",
            "created_at",
        ]