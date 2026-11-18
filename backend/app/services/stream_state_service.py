# backend/app/services/stream_state_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.models import StreamOfferState
from app.keitaro.client import keitaro_client
from app.services.campaign_service import campaign_service
from fastapi import HTTPException


class StreamStateService:
    """
    Сервис для управления локальным состоянием офферов в потоках.
    """
    
    async def get_campaign_streams_with_state(
        self, 
        db: AsyncSession, 
        campaign_id: int
    ) -> list[dict]:
        """
        Получить потоки кампании с обогащёнными данными из БД.
        Автоматически синхронизирует состояние БД с Keitaro.
        """
        # Получаем потоки из Keitaro
        streams = await campaign_service.get_campaign_streams_enriched(campaign_id)
        
        # Для каждого потока получаем состояние из БД
        for stream in streams:
            stream_id = stream["id"]
            db_state = await self.get_stream_state(db, stream_id)
            
            keitaro_offers = stream.get("offers", [])
            keitaro_offer_ids = {o["offer_id"] for o in keitaro_offers}
            
            if db_state:
                # Проверяем, есть ли офферы в БД, которых нет в Keitaro
                needs_update = False
                for db_offer in db_state:
                    if db_offer["offer_id"] not in keitaro_offer_ids and not db_offer["deleted"]:
                        # Оффер есть в БД как активный, но нет в Keitaro → помечаем как deleted
                        db_offer["deleted"] = True
                        db_offer["share"] = 0
                        needs_update = True
                
                # Если были изменения — сохраняем в БД
                if needs_update:
                    await self.update_stream_state(db, stream_id, campaign_id, db_state)
                
                # Объединяем данные из БД с данными из Keitaro
                db_offers_map = {o["offer_id"]: o for o in db_state}
                
                for offer in keitaro_offers:
                    offer_id = offer["offer_id"]
                    if offer_id in db_offers_map:
                        db_offer = db_offers_map[offer_id]
                        offer["share"] = db_offer["share"]
                        offer["deleted"] = db_offer["deleted"]
                        offer["pinned"] = db_offer["pinned"]
                
                # Добавляем удалённые офферы из БД
                for db_offer in db_state:
                    if db_offer["offer_id"] not in keitaro_offer_ids:
                        stream["offers"].append({
                            "offer_id": db_offer["offer_id"],
                            "offer_name": db_offer["offer_name"],
                            "share": db_offer["share"],
                            "state": db_offer["state"],
                            "deleted": db_offer["deleted"],
                            "pinned": db_offer["pinned"]
                        })
            else:
                # Если в БД нет данных — инициализируем из Keitaro
                offers_to_save = [
                    {
                        "offer_id": o["offer_id"],
                        "offer_name": o.get("offer_name", ""),
                        "share": o.get("share", 0),
                        "state": o.get("state", "active"),
                        "deleted": False,
                        "pinned": False
                    }
                    for o in keitaro_offers
                ]
                await self.update_stream_state(db, stream_id, campaign_id, offers_to_save)
    
        return streams
    
    async def get_stream_state(self, db: AsyncSession, stream_id: int) -> list[dict]:
        """
        Получить все офферы потока из БД (включая удалённые).
        """
        result = await db.execute(
            select(StreamOfferState)
            .where(StreamOfferState.stream_id == stream_id)
            .order_by(StreamOfferState.position)
        )
        states = result.scalars().all()
        
        return [
            {
                "offer_id": s.offer_id,
                "offer_name": s.offer_name,
                "share": s.share,
                "state": s.state,
                "deleted": s.deleted,
                "pinned": s.pinned,
                "position": s.position
            }
            for s in states
        ]
    
    async def update_stream_state(
        self, 
        db: AsyncSession, 
        stream_id: int, 
        campaign_id: int,
        offers_data: list[dict]
    ) -> None:
        """
        Сохранить изменения офферов в БД (upsert).
        """
        for position, offer in enumerate(offers_data):
            stmt = insert(StreamOfferState).values(
                stream_id=stream_id,
                campaign_id=campaign_id,
                offer_id=offer["offer_id"],
                offer_name=offer.get("offer_name", ""),
                share=offer.get("share", 0),
                state=offer.get("state", "active"),
                deleted=offer.get("deleted", False),
                pinned=offer.get("pinned", False),
                position=position
            ).on_conflict_do_update(
                constraint='uq_stream_offer',
                set_={
                    "offer_name": offer.get("offer_name", ""),
                    "share": offer.get("share", 0),
                    "state": offer.get("state", "active"),
                    "deleted": offer.get("deleted", False),
                    "pinned": offer.get("pinned", False),
                    "position": position
                }
            )
            await db.execute(stmt)
        
        await db.commit()
    
    async def sync_to_keitaro(self, db: AsyncSession, stream_id: int) -> dict:
        """
        Синхронизировать активные офферы с Keitaro.
        """
        result = await db.execute(
            select(StreamOfferState)
            .where(
                StreamOfferState.stream_id == stream_id,
                StreamOfferState.deleted == False
            )
            .order_by(StreamOfferState.position)
        )
        active_offers = result.scalars().all()
        
        offers_payload = [
            {
                "offer_id": o.offer_id,
                "share": o.share,
                "state": o.state
            }
            for o in active_offers
        ]
        
        try:
            await keitaro_client.update_stream(stream_id, {"offers": offers_payload})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка синхронизации с Keitaro: {str(e)}")
        
        return {"success": True, "synced_offers": len(offers_payload)}
    
    async def refresh_from_keitaro(
        self, 
        db: AsyncSession, 
        stream_id: int, 
        campaign_id: int
    ) -> list[dict]:
        """
        Обновить состояние из Keitaro.
        """
        result = await db.execute(
            select(StreamOfferState)
            .where(StreamOfferState.stream_id == stream_id)
        )
        current_states = {s.offer_id: s for s in result.scalars().all()}
        
        streams = await keitaro_client.get_campaign_streams(campaign_id)
        keitaro_stream = next((s for s in streams if s["id"] == stream_id), None)
        
        if not keitaro_stream:
            raise HTTPException(status_code=404, detail="Поток не найден в Keitaro")
        
        keitaro_offers = keitaro_stream.get("offers", [])
        keitaro_offer_ids = {o["offer_id"] for o in keitaro_offers}
        
        all_offers = await keitaro_client.get_offers()
        offers_map = {o["id"]: o["name"] for o in all_offers}
        
        for position, k_offer in enumerate(keitaro_offers):
            offer_id = k_offer["offer_id"]
            offer_name = offers_map.get(offer_id, f"Оффер {offer_id}")
            
            if offer_id in current_states:
                state = current_states[offer_id]
                state.share = k_offer.get("share", 0)
                state.state = k_offer.get("state", "active")
                state.position = position
            else:
                state = StreamOfferState(
                    stream_id=stream_id,
                    campaign_id=campaign_id,
                    offer_id=offer_id,
                    offer_name=offer_name,
                    share=k_offer.get("share", 0),
                    state=k_offer.get("state", "active"),
                    deleted=False,
                    pinned=False,
                    position=position
                )
                db.add(state)
        
        for offer_id, state in current_states.items():
            if offer_id not in keitaro_offer_ids and not state.deleted:
                state.deleted = True
                state.share = 0
        
        await db.commit()
        
        return await self.get_stream_state(db, stream_id)


stream_state_service = StreamStateService()
