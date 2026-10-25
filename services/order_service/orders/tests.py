
from django.test import TestCase
from rest_framework.test import APIClient


class OrderAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_orders_endpoint_is_available(self):
        response = self.client.get("/api/orders/orders/")
        self.assertNotEqual(response.status_code, 500)
