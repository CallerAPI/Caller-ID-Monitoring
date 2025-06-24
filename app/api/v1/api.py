from fastapi import APIRouter
from app.api.v1.endpoints import phone_numbers

api_router = APIRouter()

api_router.include_router(phone_numbers.router, prefix="/phone-numbers", tags=["phone-numbers"])