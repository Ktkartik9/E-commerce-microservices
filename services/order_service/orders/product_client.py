import requests


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


def reserve_stock(product_id, quantity):
    url = f"{PRODUCT_SERVICE_URL}{product_id}/reserve-stock/"

    try:
        response = requests.post(
            url,
            json={"quantity": quantity},
            timeout=5,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    return response.json()
