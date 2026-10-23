import requests
import uuid


PRODUCT_SERVICE_URL = "http://127.0.0.1:8002/api/products/"


def get_product(product_id):
    url = f"{PRODUCT_SERVICE_URL}{product_id}/"

    try:
        response = requests.get(url, timeout=5)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    return response.json()




def reserve_stock(product_id, quantity, reservation_id=None):
    if reservation_id is None:
        reservation_id = str(uuid.uuid4())

    url = f"{PRODUCT_SERVICE_URL}{product_id}/reserve-stock/"

    try:
        response = requests.post(
            url,
            json={
                "quantity": quantity,
                "reservation_id": reservation_id,
            },
            timeout=5,
        )
    except requests.RequestException:
        return {
            "success": False,
            "error": "Product Service is unavailable.",
            "status_code": 503,
            "reservation_id": reservation_id,
        }

    try:
        data = response.json()
    except ValueError:
        data = {"error": "Invalid response from Product Service."}

    if response.status_code == 200:
        return {
            "success": True,
            "data": data,
            "reservation_id": reservation_id,
        }

    return {
        "success": False,
        "error": data.get("error", "Stock reservation failed."),
        "status_code": response.status_code,
        "details": data,
        "reservation_id": reservation_id,
    }



def release_stock(product_id, quantity, reservation_id):
    url = f"{PRODUCT_SERVICE_URL}{product_id}/release-stock/"

    try:
        response = requests.post(
            url,
            json={"reservation_id": reservation_id},
            timeout=5,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    return data
