# backend/app/api/routes.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import CampaignCreateRequest
from app.services.campaign_service import campaign_service
from app.services.stream_state_service import stream_state_service
from app.database import get_db
from app.core.config import settings
from app.keitaro.client import keitaro_client

router = APIRouter(prefix="/api", tags=["Campaigns"])

@router.get("/campaigns")
async def get_campaigns():
    """Получить список кампаний пользователя."""
    campaigns = await campaign_service.get_user_campaigns(surname=settings.SURNAME)
    return {"campaigns": campaigns}

@router.post("/campaigns/create")
async def create_campaign(payload: CampaignCreateRequest):
    """Создать новую кампанию."""
    result = await campaign_service.create_campaign_with_streams(
        name=payload.name,
        geo_code=payload.geo_code,
        offer_id=payload.offer_id,
        surname=settings.SURNAME
    )
    return result

@router.get("/offers")
async def get_offers():
    """Получить список всех офферов."""
    raw_offers = await keitaro_client.get_offers()
    formatted_offers = [{"id": o["id"], "name": o["name"]} for o in raw_offers]
    return {"offers": formatted_offers}

@router.get("/campaigns/{campaign_id}/streams")
async def get_campaign_streams(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить потоки кампании с состоянием из БД."""
    streams = await stream_state_service.get_campaign_streams_with_state(db, campaign_id)
    return {"streams": streams}

@router.put("/streams/{stream_id}")
async def update_stream(
    stream_id: int,
    stream_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Обновить состояние офферов в БД."""
    campaign_id = stream_data.get("campaign_id", 0)
    offers_data = stream_data.get("offers", [])
    await stream_state_service.update_stream_state(db, stream_id, campaign_id, offers_data)
    return {"success": True}

@router.post("/streams/{stream_id}/sync")
async def sync_stream_to_keitaro(
    stream_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Синхронизировать активные офферы с Keitaro."""
    return await stream_state_service.sync_to_keitaro(db, stream_id)

@router.post("/streams/{stream_id}/refresh")
async def refresh_stream_from_keitaro(
    stream_id: int,
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Обновить состояние из Keitaro."""
    updated_state = await stream_state_service.refresh_from_keitaro(db, stream_id, campaign_id)
    return {"offers": updated_state}
