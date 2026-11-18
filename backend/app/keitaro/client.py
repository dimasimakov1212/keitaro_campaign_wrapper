# backend/app/keitaro/client.py

import httpx
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class KeitaroClient:
    def __init__(self):
        self.base_url = settings.KEITARO_API_URL.rstrip('/')
        self.api_key = settings.KEITARO_API_KEY

    async def _request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        params = kwargs.pop("params", {})
        params["api_key"] = self.api_key
        
        headers = kwargs.pop("headers", {})
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        if method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/json"

        # --- ДОБАВЛЯЕМ ЛОГИРОВАНИЕ ДЛЯ ОТЛАДКИ ---
        logger.warning(f"===> Keitaro API Request: {method} {url}")
        logger.warning(f"===> Params: {params}")
        if "json" in kwargs:
            logger.warning(f"===> JSON Payload: {json.dumps(kwargs['json'])}")
        # -----------------------------------------

        # verify=False отключает проверку SSL-сертификата (решает проблему с самоподписанными сертификатами)
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            try:
                response = await client.request(
                    method, url, params=params, headers=headers, timeout=15.0, **kwargs
                )
                if not response.is_success:
                    logger.error(f"<=== Keitaro API Error: {response.status_code}")
                    logger.error(f"<=== Response text: {response.text}")
                    response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"<=== HTTP Error: {e}")
                raise
            except httpx.RequestError as e:
                logger.error(f"<=== Request Error: {e}")
                raise
            except Exception as e:
                logger.error(f"<=== Unexpected Error: {e}")
                raise

    # --- Справочники ---
    async def get_domains(self):
        """Получение списка доменов"""
        return await self._request("GET", "domains")

    async def get_groups(self, group_type: str = "campaigns"):
        """Получение списка групп"""
        return await self._request("GET", "groups", params={"type": group_type})

    async def create_group(self, group_data: dict):
        """Создание группы"""
        return await self._request("POST", "groups", json=group_data)

    async def get_traffic_sources(self):
        """Получение списка источников траффика"""
        return await self._request("GET", "traffic_sources")

    async def get_offers(self):
        """Получение списка офферов"""
        return await self._request("GET", "offers")

    # --- Кампании и потоки ---
    async def get_campaigns(self):
        """Получить список всех кампаний из Keitaro"""
        return await self._request("GET", "campaigns")
    
    async def create_campaign(self, campaign_data: dict):
        """Создать кампанию"""
        return await self._request("POST", "campaigns", json=campaign_data)

    async def create_stream(self, stream_data: dict):
        """Создать поток"""
        return await self._request("POST", "streams", json=stream_data)
        
    async def get_campaign_streams(self, campaign_id: int):
        """Получить потоки кампании"""
        return await self._request("GET", f"campaigns/{campaign_id}/streams")
        
    async def update_stream(self, stream_id: int, stream_data: dict):
        """Обновляет поток"""
        # 1. Получаем текущий поток
        current_stream = await self._request("GET", f"streams/{stream_id}")
        
        # 2. Объединяем: берём все поля из текущего потока,
        #    но перезаписываем те, что пришли в stream_data
        updated_data = {**current_stream, **stream_data}
        
        # 3. Отправляем полный объект
        return await self._request("PUT", f"streams/{stream_id}", json=updated_data)


keitaro_client = KeitaroClient()