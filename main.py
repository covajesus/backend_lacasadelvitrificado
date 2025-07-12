from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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

app = FastAPI(root_path="/api")
application = app

#FILES_DIR = "C:/Users/jesus/berger_seidle_backend/files"

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

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
