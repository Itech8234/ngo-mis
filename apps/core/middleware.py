"""Middleware storing the current request for signals and services."""
import threading

from django.shortcuts import render

_current = threading.local()


def get_current_request():
    return getattr(_current, "request", None)


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class CurrentRequestMiddleware:
    """Exposes the current request to non-request code (signals, services)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _current.request = request
        try:
            return self.get_response(request)
        finally:
            _current.request = None


class Branded404Middleware:
    """Render the branded not-found page, including while DEBUG is enabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code != 404 or response.get("X-GHDI-Not-Found"):
            return response
        response = render(
            request,
            "errors/404.html",
            {
                "title": "Page not found",
                "message": "The page you are looking for does not exist or may have been moved.",
            },
            status=404,
        )
        response["X-GHDI-Not-Found"] = "1"
        return response
