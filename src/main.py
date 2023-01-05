from typing import Optional
from fastapi import FastAPI, Request

import src.proxy as proxy

api = FastAPI()


@api.head("/v2/{path:path}")
@api.get("/v2/{path:path}")
def v2(
    request: Request,
    path: Optional[str] = "",
    service: Optional[str] = None,
    scope: Optional[str] = None,
):
    return proxy.handle_v2(request, path, service=service, scope=scope)


@api.get("{image:path}/")
def get_image(image: str):
    return proxy.browse_image(image)
