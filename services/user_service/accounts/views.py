
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User
from rest_framework.pagination import PageNumberPagination
from django.db import models




@api_view(["GET"])
def health_check(request):
    return Response({
        "service": "User Service",
        "status": "healthy",
        "version": "1.0.0",
        "message": "User Service API is working!"
    })



@api_view(["POST"])
def register_user(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        return Response(
            {
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "bio": user.bio,
        "location": user.location,
    })




@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user

    allowed_fields = ["first_name", "last_name", "bio", "location"]

    for field in allowed_fields:
        if field in request.data:
            setattr(user, field, request.data[field])

    user.save()

    return Response(
        {
            "message": "Profile updated successfully",
            "first_name": user.first_name,
            "last_name": user.last_name,
            "bio": user.bio,
            "location": user.location,
        },
        status=status.HTTP_200_OK,
    )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user

    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")

    if not current_password or not new_password:
        return Response(
            {"error": "Current password and new password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.check_password(current_password):
        return Response(
            {"error": "Current password is incorrect."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(new_password, user=user)
    except ValidationError as error:
        return Response(
            {"error": list(error.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save()

    return Response(
        {"message": "Password changed successfully."},
        status=status.HTTP_200_OK,
    )





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_list(request):

    search = request.query_params.get("search", "").strip()
    location = request.query_params.get("location", "").strip()

    if location:
        users = User.objects.all().order_by("id")
        users = users.filter(location__icontains=location)

    if search:
        users = users.filter(
            models.Q(username__icontains=search)
            | models.Q(first_name__icontains=search)
            | models.Q(last_name__icontains=search)
            | models.Q(location__icontains=search)
        )

    paginator = PageNumberPagination()
    paginator.page_size = 10

    page = paginator.paginate_queryset(users, request)

    data = []

    for user in page:
        data.append({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "bio": user.bio,
            "location": user.location,
        })

    return paginator.get_paginated_response(data)




@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    user = request.user
    user.delete()

    return Response(
        {"message": "Your account has been deleted successfully."},
        status=status.HTTP_200_OK,
    )