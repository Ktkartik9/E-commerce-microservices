from django.urls import path

from .views import process_payment

urlpatterns = [
    path("process/",process_payment,name="process-payment",),
]

