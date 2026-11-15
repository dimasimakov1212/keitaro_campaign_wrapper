# backend/app/keitaro/client.py

import httpx
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
        if method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/json"

        # verify=False отключает проверку SSL-сертификата (решает проблему с самоподписанными сертификатами)
        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.request(
                    method, 
                    url, 
                    params=params, 
                    headers=headers,
                    **kwargs
                )
                
                # Если статус не 2xx, выводим подробную информацию перед выбросом ошибки
                if not response.is_success:
                    logger.error(f"Keitaro API Error: {response.status_code}")
                    logger.error(f"Response text: {response.text}")
                    response.raise_for_status()
                
                # Пытаемся распарсить JSON
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error: {e}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request Error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                raise

    # --- Методы для справочников ---
    async def get_domains(self):
        return await self._request("GET", "domains")

    async def get_groups(self):
        return await self._request("GET", "groups")

    async def get_sources(self):
        return await self._request("GET", "sources")

    # --- Методы для создания кампании ---
    async def create_campaign(self, campaign_data: dict):
        return await self._request("POST", "campaigns", json=campaign_data)

    async def create_stream(self, stream_data: dict):
        return await self._request("POST", "streams", json=stream_data)

    # --- Методы для редактора ---
    async def get_offers(self):
        return await self._request("GET", "offers")

    async def get_campaign(self, campaign_id: int):
        return await self._request("GET", f"campaigns/{campaign_id}")

    async def get_streams(self, campaign_id: int):
        return await self._request("GET", "streams", params={"campaign_id": campaign_id})

    async def update_stream(self, stream_id: int, stream_data: dict):
        return await self._request("PUT", f"streams/{stream_id}", json=stream_data)

    async def delete_stream(self, stream_id: int):
        return await self._request("DELETE", f"streams/{stream_id}")

keitaro_client = KeitaroClient()