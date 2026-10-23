import uuid
from rest_framework import generics
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db import models  
from .models import Product, Category, StockReservation


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).order_by("-created_at")

        category_id = self.request.query_params.get("category")

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        search = self.request.query_params.get("search", "").strip()
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        if search:
            queryset = queryset.filter(name__icontains=search)

        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer



class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer





@api_view(["PATCH"])
def update_product_stock(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    stock = request.data.get("stock")

    if stock is None:
        return Response(
            {"error": "Stock is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
        return Response(
            {"error": "Stock must be a non-negative integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product.stock = stock
    product.save(update_fields=["stock", "updated_at"])

    return Response(
        {
            "message": "Stock updated successfully.",
            "product_id": product.id,
            "stock": product.stock,
        },
        status=status.HTTP_200_OK,
    )





@api_view(["POST"])
def reserve_product_stock(request, pk):
    quantity = request.data.get("quantity")
    reservation_id = request.data.get("reservation_id")

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
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
            if existing.product_id != pk or existing.quantity != quantity:
                return Response(
                    {"error": "Reservation ID was already used for a different request."},
                    status=status.HTTP_409_CONFLICT,
                )

            return Response(
                {
                    "message": "Reservation already exists.",
                    "product_id": existing.product_id,
                    "reserved_quantity": existing.quantity,
                    "reservation_id": str(existing.reservation_id),
                    "released": existing.is_released,
                },
                status=status.HTTP_200_OK,
            )

        updated = Product.objects.filter(
            pk=pk,
            is_active=True,
            stock__gte=quantity,
        ).update(
            stock=models.F("stock") - quantity
        )

        if updated == 0:
            product = Product.objects.filter(pk=pk).first()

            if product is None:
                return Response(
                    {"error": "Product not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not product.is_active:
                return Response(
                    {"error": "Product is unavailable."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "error": "Insufficient stock.",
                    "available_stock": product.stock,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reservation = StockReservation.objects.create(
            product_id=pk,
            reservation_id=reservation_id,
            quantity=quantity,
        )

        product = Product.objects.get(pk=pk)

    return Response(
        {
            "message": "Stock reserved successfully.",
            "product_id": product.id,
            "reserved_quantity": quantity,
            "remaining_stock": product.stock,
            "reservation_id": str(reservation.reservation_id),
            "released": False,
        },
        status=status.HTTP_200_OK,
    )





@api_view(["POST"])
def release_product_stock(request, pk):
    reservation_id = request.data.get("reservation_id")

    if not reservation_id:
        return Response(
            {"error": "Reservation ID is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        reservation_id = uuid.UUID(str(reservation_id))
    except (ValueError, TypeError, AttributeError):
        return Response(
            {"error": "A valid reservation ID is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        reservation = StockReservation.objects.filter(
            reservation_id=reservation_id,
            product_id=pk,
        ).first()

        if reservation is None:
            return Response(
                {"error": "Reservation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if reservation.is_released:
            return Response(
                {
                    "message": "Stock was already released.",
                    "reservation_id": str(reservation.reservation_id),
                    "released_quantity": reservation.quantity,
                    "already_released": True,
                },
                status=status.HTTP_200_OK,
            )

        updated = StockReservation.objects.filter(
            pk=reservation.pk,
            is_released=False,
        ).update(is_released=True)

        if updated == 0:
            return Response(
                {
                    "message": "Stock was already released.",
                    "reservation_id": str(reservation.reservation_id),
                    "already_released": True,
                },
                status=status.HTTP_200_OK,
            )

        Product.objects.filter(pk=pk).update(
            stock=models.F("stock") + reservation.quantity
        )

        product = Product.objects.get(pk=pk)

    return Response(
        {
            "message": "Stock released successfully.",
            "product_id": product.id,
            "released_quantity": reservation.quantity,
            "remaining_stock": product.stock,
            "reservation_id": str(reservation.reservation_id),
            "already_released": False,
        },
        status=status.HTTP_200_OK,
    )
