from fastapi import FastAPI
from .auth import router as auth_router
from .admin import router as admin_router
from .products import router as products_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(products_router)