import requests

from typing import Optional
from fastapi import Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse


REGISTRY_HOST = ""
REGISTRY_PREFIX = ""
HOST = "localhost"
MAX_RESPONSE_SIZE = 3200000
VERIFY_REQUEST = False
PROXY_RES_EXCLUDED_HEADERS = [
    # Certain response headers should NOT be just tunneled through.  These
    # are they.  For more info, see:
    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    # Although content-encoding is not listed among the hop-by-hop headers,
    # it can cause trouble as well.  Just let the server set the value as
    # it should be.
    "content-encoding",
]


def _response_content_iter(size, source):
    for idx in range(0, len(source), size):
        yield source[idx : (idx + size)]


def _format_www_authenticate_header(value: str):
    # Reformats the www-auth header because of the proxy:
    # Hides the GCP project ID under "scope" and replaces the token endpoint hostname as well
    return value.replace(
        f"https://{REGISTRY_HOST}/v2/token", f"https://{HOST}/v2/token"
    ).replace(f"repository:{REGISTRY_PREFIX}/", "repository:")


def handle_v2(
    request: Request,
    path: Optional[str] = "",
    service: Optional[str] = None,
    scope: Optional[str] = None,
):
    registry_url = f"https://{REGISTRY_HOST}/v2/"
    if path != "":
        registry_url = (
            f"{registry_url}{path}"
            if path == "token"
            else f"{registry_url}{REGISTRY_PREFIX}/{path}"
        )

    req_args = {
        "headers": {
            key: value for key, value in request.headers.items() if key != "host"
        },
        "params": {},
    }

    if service:
        req_args["params"]["service"] = service

    # Needs to add the registry prefix to the scope
    if scope:
        # Adds back the prefix removed from a prev response from the Www-Authenticate header
        req_args["params"]["scope"] = scope.replace(
            "repository:", f"repository:{REGISTRY_PREFIX}/"
        )

    response = requests.request(
        method=request.method, url=registry_url, verify=VERIFY_REQUEST, **req_args
    )

    # If the request has not been authenticated, the registry will respond with a HTTP header
    # to get the authentication token.
    if response.headers.get("Www-Authenticate"):
        response.headers["Www-Authenticate"] = _format_www_authenticate_header(
            response.headers["Www-Authenticate"]
        )

    res_args = {
        "status_code": response.status_code,
        "headers": {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in PROXY_RES_EXCLUDED_HEADERS
        },
    }

    if MAX_RESPONSE_SIZE and len(response.content) > MAX_RESPONSE_SIZE:
        # Streaming the response instead for the large response size
        return StreamingResponse(
            _response_content_iter(MAX_RESPONSE_SIZE, response.content), **res_args,
        )

    return Response(response.content, **res_args,)


def browse_image(image: str):
    return RedirectResponse(
        f"https://{REGISTRY_HOST}/{REGISTRY_PREFIX}/{image}"
    )
