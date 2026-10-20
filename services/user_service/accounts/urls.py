
from django.urls import path

from .views import health_check, register_user, user_list, user_profile, update_profile ,change_password,user_list,delete_account

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("register/", register_user, name="register-user"),
    path("profile/", user_profile, name="user-profile"),
    path("profile/update/", update_profile, name="update-profile"),
    path("change-password/", change_password, name="change-password"),
    path("list/", user_list, name="user-list"),
    path("delete-account/", delete_account, name="delete-account"),
]
