import uuid

from django.db import models


class Inventory(models.Model):
    product_id = models.IntegerField(unique=True)
    available_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Product {self.product_id} - Stock {self.available_quantity}"


class StockReservation(models.Model):
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    reservation_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    quantity = models.PositiveIntegerField()
    is_released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.reservation_id)