# backend/app/api/routes.py

from fastapi import APIRouter, HTTPException
from app.schemas import CampaignCreateRequest
from app.services.campaign_service import campaign_service
from app.core.config import settings
from app.keitaro.client import keitaro_client

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


@router.get("/offers")
async def get_offers():
    """Получить список офферов"""

    try:
        raw_offers = await keitaro_client.get_offers()
        # Оставляем только нужные поля, чтобы не грузить сеть
        formatted_offers = [{"id": o["id"], "name": o["name"]} for o in raw_offers]
        return {"offers": formatted_offers}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения офферов: {str(e)}")
