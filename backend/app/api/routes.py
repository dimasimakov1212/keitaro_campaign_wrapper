# backend/app/api/routes.py

from fastapi import APIRouter
from app.schemas import CampaignCreateRequest
from app.services.campaign_service import campaign_service
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["Campaigns"])

@router.get("/campaigns")
async def get_campaigns():
    """
    Получить список кампаний пользователя (отфильтрованных по префиксу).
    """
    campaigns = await campaign_service.get_user_campaigns(surname=settings.SURNAME)
    return {"campaigns": campaigns}


@router.post("/campaigns/create")
async def create_campaign(payload: CampaignCreateRequest):
    """
    Создание кампании
    """
    result = await campaign_service.create_campaign_with_streams(
        name=payload.name,
        geo_code=payload.geo_code,
        offer_id=payload.offer_id,
        surname=settings.SURNAME
    )
    return result
