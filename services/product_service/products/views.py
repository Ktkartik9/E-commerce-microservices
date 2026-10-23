from rest_framework import generics
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction


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

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return Response(
            {"error": "Quantity must be a positive integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():

            product = Product.objects.select_for_update().get(pk=pk)

            if not product.is_active:
                return Response(
                    {"error": "Product is unavailable."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if quantity > product.stock:
                return Response(
                    {
                        "error": "Insufficient stock.",
                        "available_stock": product.stock,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            product.stock -= quantity

            product.save(update_fields=["stock", "updated_at"])

            remaining_stock = product.stock

    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "message": "Stock reserved successfully.",
            "product_id": product.id,
            "reserved_quantity": quantity,
            "remaining_stock": remaining_stock,
        },
        status=status.HTTP_200_OK,
    )




@api_view(["POST"])
def release_product_stock(request, pk):

    quantity = request.data.get("quantity")

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return Response(
            {"error": "Quantity must be a positive integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=pk)

            product.stock += quantity
            product.save(update_fields=["stock", "updated_at"])

            remaining_stock = product.stock

    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "message": "Stock released successfully.",
            "product_id": product.id,
            "released_quantity": quantity,
            "remaining_stock": remaining_stock,
        },
        status=status.HTTP_200_OK,
    )
