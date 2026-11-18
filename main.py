from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import os
from fastapi.middleware.cors import CORSMiddleware
from app.backend.routers.authentications import authentications
from app.backend.routers.regions import regions
from app.backend.routers.communes import communes
from app.backend.routers.locations import locations
from app.backend.routers.products import products
from app.backend.routers.files import files
from app.backend.routers.suppliers import suppliers
from app.backend.routers.categories import categories
from app.backend.routers.unit_measures import unit_measures
from app.backend.routers.inventories import inventories
from app.backend.routers.movement_types import movement_types
from app.backend.routers.settings import settings
from app.backend.routers.customers import customers
from app.backend.routers.sales import sales
from app.backend.routers.shoppings import shoppings
from app.backend.routers.supplier_categories import supplier_categories
from app.backend.routers.kardex import kardex
from app.backend.routers.dtes import dtes
from app.backend.routers.budgets import budgets
from app.backend.routers.whatsapp import whatsapp
from app.backend.routers.samples import samples
from app.backend.routers.unit_sales import unit_sales
from app.backend.routers.internal_uses import internal_uses
from app.backend.routers.promotions import promotions
from app.backend.routers.advertising import advertising
from app.backend.routers.error_logs import error_logs
from app.backend.classes.error_log_class import ErrorLogClass

app = FastAPI(root_path="/api")
application = app


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def _safe_request_body(request: Request):
    try:
        return await request.body()
    except Exception:
        return None


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Loguear 4xx/5xx de negocio (no 401 rutinarios de auth para no llenar la tabla)
    if exc.status_code >= 400 and exc.status_code != 401:
        body = await _safe_request_body(request)
        ErrorLogClass.log(
            message=str(exc.detail) if exc.detail is not None else f"HTTP {exc.status_code}",
            level="warning" if 400 <= exc.status_code < 500 else "error",
            source="http_exception",
            method=request.method,
            path=str(request.url.path),
            status_code=exc.status_code,
            detail=str(exc.detail),
            request_body=body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else body,
            client_ip=_client_ip(request),
            exc=exc if exc.status_code >= 500 else None,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    ErrorLogClass.log(
        message="Error de validación de request",
        level="warning",
        source="validation",
        method=request.method,
        path=str(request.url.path),
        status_code=422,
        detail=str(exc.errors()),
        request_body=exc.body if hasattr(exc, "body") else None,
        client_ip=_client_ip(request),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    body = await _safe_request_body(request)
    ErrorLogClass.log(
        message=str(exc) or type(exc).__name__,
        level="error",
        source="unhandled",
        method=request.method,
        path=str(request.url.path),
        status_code=500,
        request_body=body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else body,
        client_ip=_client_ip(request),
        exc=exc,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

#FILES_DIR = "C:/Users/jesus/OneDrive/Escritorio/backend-lacasadelvitrificado/files"

# Montar como directorio estático
#app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

os.environ['SECRET_KEY'] = '7de4c36b48fce8dcb3a4bb527ba62d789ebf3d3a7582472ee49d430b01a7f868'
os.environ['ALGORITHM'] = 'HS256'

origins = [
    "*",
    "https://newerp-ghdegyc9cpcpc6gq.eastus-01.azurewebsites.net",
    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(authentications)
app.include_router(regions)
app.include_router(communes)
app.include_router(locations)
app.include_router(products)
app.include_router(files)
app.include_router(suppliers)
app.include_router(categories)
app.include_router(unit_measures)
app.include_router(inventories)
app.include_router(movement_types)
app.include_router(settings)
app.include_router(customers)
app.include_router(sales)
app.include_router(shoppings)
app.include_router(supplier_categories)
app.include_router(kardex)
app.include_router(dtes)
app.include_router(budgets)
app.include_router(whatsapp)
app.include_router(samples)
app.include_router(unit_sales)
app.include_router(internal_uses)
app.include_router(promotions)
app.include_router(advertising)
app.include_router(error_logs)

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
