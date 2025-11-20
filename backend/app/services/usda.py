import httpx
from typing import Optional, Dict
from backend.app.database import get_settings

settings = get_settings()


class USDAService:
    """Service for USDA FoodData Central API"""
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self):
        self.api_key = settings.usda_api_key

    async def search_foods(
            self,
            query: str,
            data_type: Optional[str] = None,
            page_size: int = 25,
            page_number: int = 1
    ) -> Optional[Dict]:
        """
        Search USDA food database

        Args:
            query: Search term
            data_type: Filter by data type (Survey, Foundation, Branded, SR Legacy)
            page_size: Number of results (max 200)
            page_number: Page number

        Returns:
            Search results with nutritional data
        """
        params = {
            "api_key": self.api_key,
            "query": query,
            "pageSize": page_size,
            "pageNumber": page_number
        }

        if data_type:
            params["dataType"] = data_type

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/foods/search",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error searching USDA foods: {e}")
                return None

    async def get_food_details(self, fdc_id: int) -> Optional[Dict]:
        """
        Get detailed information for a specific food

        Args:
            fdc_id: FoodData Central ID

        Returns:
            Detailed food information
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/food/{fdc_id}",
                    params={"api_key": self.api_key},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error getting food details: {e}")
                return None