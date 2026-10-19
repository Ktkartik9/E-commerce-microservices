
from django.urls import path

from .views import health_check, register_user, user_profile, update_profile

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("register/", register_user, name="register-user"),
    path("profile/", user_profile, name="user-profile"),
    path("profile/update/", update_profile, name="update-profile"),
]
