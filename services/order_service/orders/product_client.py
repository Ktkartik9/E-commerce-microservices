
import requests
import uuid
import os


PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://127.0.0.1:8002/api/products",
)

INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL",
    "http://127.0.0.1:8004/api/inventory",
)

# Django rejects Docker service names containing underscores.
SERVICE_HEADERS = {
    "Host": "localhost",
}


def get_product(product_id):
    url = f"{PRODUCT_SERVICE_URL.rstrip('/')}/{product_id}/"

    try:
        response = requests.get(
            url,
            headers=SERVICE_HEADERS,
            timeout=5,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    return response.json()


def reserve_stock(product_id, quantity, reservation_id=None):
    if reservation_id is None:
        reservation_id = uuid.uuid4()

    url = f"{INVENTORY_SERVICE_URL.rstrip('/')}/{product_id}/reserve/"

    payload = {
        "quantity": quantity,
        "reservation_id": str(reservation_id),
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=SERVICE_HEADERS,
            timeout=5,
        )

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code in [200, 201]:
            return {
                "success": True,
                "data": data,
                "reservation_id": str(reservation_id),
                "status_code": response.status_code,
            }

        return {
            "success": False,
            "data": data,
            "reservation_id": str(reservation_id),
            "status_code": response.status_code,
            "details": data,
        }

    except requests.RequestException as exc:
        return {
            "success": False,
            "data": {},
            "reservation_id": str(reservation_id),
            "status_code": None,
            "details": str(exc),
        }


def release_stock(product_id, quantity, reservation_id):
    url = f"{INVENTORY_SERVICE_URL.rstrip('/')}/{product_id}/release/"

    payload = {
        "reservation_id": str(reservation_id),
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=SERVICE_HEADERS,
            timeout=5,
        )

        if response.status_code == 200:
            return response.json()

        return None

    except requests.RequestException:
        return None
