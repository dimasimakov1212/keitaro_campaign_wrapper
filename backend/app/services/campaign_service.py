# backend/app/services/campaign_service.py

from fastapi import HTTPException
from app.keitaro.client import keitaro_client


class CampaignService:
    async def create_campaign_with_streams(self, name: str, geo_code: str, offer_id: int, surname: str) -> dict:
        try:
            # 1. Логика работы с Группой: ищем или создаем
            target_group_name = f"test_{surname.lower()}_group"
            groups = await keitaro_client.get_groups()
            
            # Ищем существующую группу
            group_id = next((g["id"] for g in groups if g["name"].lower() == target_group_name), None)
            
            if not group_id:
                new_group = await keitaro_client.create_group({
                    "name": target_group_name,
                    "type": "campaigns"
                })
                group_id = new_group["id"]

            # 2. Логика работы с Доменом: берем первый активный
            domains = await keitaro_client.get_domains()
            active_domains = [d for d in domains if d.get("state") == "active" or d.get("status") == "active"]

            if not active_domains:
                raise HTTPException(status_code=500, detail="В Keitaro нет активных доменов")
            
            domain_id = active_domains[0]["id"]

            # 3. Логика работы с Источником: берем первый активный
            sources = await keitaro_client.get_traffic_sources()
            active_sources = [s for s in sources if s.get("state") == "active"]

            if not active_sources:
                raise HTTPException(status_code=500, detail="В Keitaro нет активных источников трафика")
            source_id = active_sources[0]["id"]

            # 4. Создание кампании
            campaign_payload = {
                "name": name,
                "domain_id": domain_id,
                "group_id": group_id,
                "traffic_source_id": source_id,
                "state": "active"
            }
            
            campaign_response = await keitaro_client.create_campaign(campaign_payload)
            campaign_id = campaign_response.get("id")
            
            if not campaign_id:
                raise HTTPException(status_code=500, detail="Не удалось получить ID созданной кампании из ответа Keitaro")

            # 5. Создание Потока 1: Гео -> Google
            stream1_payload = {
                "campaign_id": campaign_id,
                "name": f"Geo {geo_code.upper()} -> Google",
                "filters": [{"type": "geo", "value": geo_code.upper()}],
                "action": {"type": "redirect", "url": "https://google.com"}
            }
            await keitaro_client.create_stream(stream1_payload)

            # 6. Создание Потока 2: Все остальные -> Оффер
            stream2_payload = {
                "campaign_id": campaign_id,
                "name": "Default -> Offer",
                "filters": [], 
                "action": {"type": "offer", "offer_id": offer_id}
            }
            await keitaro_client.create_stream(stream2_payload)

            return {
                "success": True,
                "message": "Кампания и 2 потока успешно созданы",
                "campaign_id": campaign_id,
                "campaign_name": name,
                "details": {
                    "used_domain_id": domain_id,
                    "used_group_id": group_id,
                    "used_source_id": source_id
                }
            }

        except HTTPException:
            # Пробрасываем HTTP-ошибки как есть
            raise
        except Exception as e:
            # Ловим любые другие ошибки и оборачиваем в 500
            raise HTTPException(status_code=500, detail=f"Ошибка бизнес-логики при создании кампании: {str(e)}")

campaign_service = CampaignService()
