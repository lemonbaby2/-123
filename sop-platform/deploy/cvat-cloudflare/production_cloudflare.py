"""CVAT production settings for Cloudflare Tunnel access.

Keep this file outside the container image and mount it read-only.  The public
origin list is supplied by Docker Compose so Quick Tunnel host changes can be
updated without rebuilding CVAT or touching its database volumes.
"""

import os
from urllib.parse import urlparse

from .production import *  # noqa: F403


def _origins(value: str) -> list[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


CSRF_TRUSTED_ORIGINS = _origins(os.environ.get("CVAT_CSRF_TRUSTED_ORIGINS", ""))
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True


class CloudflareOriginHostMiddleware:
    """Restore the browser-facing host when Quick Tunnel rewrites Host.

    The existing tunnel is intentionally started with ``--http-host-header``
    so Traefik can keep its LAN host rule.  CVAT export URLs must nevertheless
    point back to the public HTTPS origin.  Only an explicitly trusted Origin
    is allowed to influence the request host.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN", "").rstrip("/")
        if origin in CSRF_TRUSTED_ORIGINS:
            parsed = urlparse(origin)
            if parsed.scheme == "https" and parsed.netloc:
                request.META["HTTP_HOST"] = parsed.netloc
                request.META["HTTP_X_FORWARDED_HOST"] = parsed.netloc
                request.META["SERVER_PORT"] = "443"
                request.META["wsgi.url_scheme"] = "https"
                request.META["HTTP_X_FORWARDED_PROTO"] = "https"
        return self.get_response(request)


MIDDLEWARE = [
    "cvat.settings.production_cloudflare.CloudflareOriginHostMiddleware",
    *MIDDLEWARE,  # noqa: F405
]
