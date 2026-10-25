
import uuid
import requests

PAYMENT_SERVICE_URL = "http://127.0.0.1:8005/api/payments"


def process_payment(order_id, amount, idempotency_key=None):
    if idempotency_key is None:
        idempotency_key = uuid.uuid4()

    url = f"{PAYMENT_SERVICE_URL}/process/"

    payload = {
        "order_id": order_id,
        "amount": str(amount),
        "idempotency_key": str(idempotency_key),
        "simulate_failure": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=5)

        try:
            data = response.json()
        except ValueError:
            data = {}

        payment_status = data.get("status")

        return {
            "success": (
                response.status_code in [200, 201]
                and payment_status == "success"
            ),
            "status_code": response.status_code,
            "data": data,
            "idempotency_key": str(idempotency_key),
        }

    except requests.RequestException as exc:
        return {
            "success": False,
            "status_code": None,
            "data": {"error": str(exc)},
            "idempotency_key": str(idempotency_key),
        }
