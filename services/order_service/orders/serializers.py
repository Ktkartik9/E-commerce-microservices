
from rest_framework import serializers
from .models import Order, OrderItem



class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "product_id",
            "quantity",
            "price",
        ]
        read_only_fields = ["id", "order"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Quantity must be at least 1."
            )
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than zero."
            )
        return value



class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status = serializers.ReadOnlyField()
    def validate_user_id(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "User ID must be greater than zero."
            )
        return value

    class Meta:
        model = Order
        fields = [
            "id",
            "user_id",
            "total_amount",
            "status",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
        "id",
        "total_amount",
        "status",
        "created_at",
        "updated_at",
    ]
