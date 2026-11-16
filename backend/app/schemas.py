# backend/app/schemas.py

from pydantic import BaseModel, Field, field_validator
from app.core.config import settings

class CampaignCreateRequest(BaseModel):
    name: str = Field(..., description="Название кампании")
    geo_code: str = Field(..., description="Гео-код страны, например: RU, US, DE")
    offer_id: int = Field(..., description="ID оффера в Keitaro")

    @field_validator('name')
    @classmethod
    def validate_name_prefix(cls, v: str) -> str:
        expected_prefix = f"test_{settings.SURNAME.lower()}_"
        if not v.lower().startswith(expected_prefix):
            raise ValueError(f"Название кампании должно начинаться с префикса 'test_{settings.SURNAME.lower()}_'")
        return v
