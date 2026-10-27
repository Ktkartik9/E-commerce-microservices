
import os

import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt


SERVICE_URLS = {
    "users": os.getenv("USER_SERVICE_URL", "http://127.0.0.1:8001"),
    "products": os.getenv("PRODUCT_SERVICE_URL", "http://127.0.0.1:8002"),
    "orders": os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8003"),
    "inventory": os.getenv("INVENTORY_SERVICE_URL", "http://127.0.0.1:8004"),
    "payments": os.getenv("PAYMENT_SERVICE_URL", "http://127.0.0.1:8005"),
}


@csrf_exempt
def proxy_request(request, service, path=""):
    base_url = SERVICE_URLS.get(service)

    if not base_url:
        return JsonResponse(
            {"error": "Service not found."},
            status=404,
        )

    target_url = f"{base_url.rstrip('/')}{request.path}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ("host", "content-length", "connection")
    }

    try:
        response = requests.request(
            method=request.method,
            url=target_url,
            params=request.GET,
            data=request.body,
            headers=headers,
            timeout=10,
            allow_redirects=False,
        )

        excluded_headers = {
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        }

        response_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in excluded_headers
        }

        return HttpResponse(
        response.content,
        status=response.status_code,
        headers={
        key: value
        for key, value in response_headers.items()
        if key.lower() != "content-type"
    },
    content_type=response.headers.get("Content-Type"),
    )
        

    except requests.RequestException:
        return JsonResponse(
            {
                "error": "Microservice is unavailable.",
                "service": service,
            },
            status=502,
        )
