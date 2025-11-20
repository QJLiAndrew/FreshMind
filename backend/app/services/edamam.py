import httpx
from typing import Optional, Dict, List
from backend.app.database import get_settings

settings = get_settings()


class EdamamRecipeService:
    """Service for Edamam Recipe Search API"""
    BASE_URL = "https://api.edamam.com/api/recipes/v2"

    def __init__(self):
        self.app_id = settings.edamam_recipe_app_id
        self.app_key = settings.edamam_recipe_app_key

    async def search_recipes(
            self,
            query: str,
            diet: Optional[str] = None,
            health: Optional[List[str]] = None,
            cuisine_type: Optional[str] = None,
            meal_type: Optional[str] = None,
            calories: Optional[str] = None,
    ) -> Optional[Dict]:
        """Search for recipes with filters"""
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "q": query,
            "type": "public"
        }

        if diet: params["diet"] = diet
        if health:
            # Edamam expects multiple 'health' parameters, httpx handles lists automatically
            params["health"] = health
        if cuisine_type: params["cuisineType"] = cuisine_type
        if meal_type: params["mealType"] = meal_type
        if calories: params["calories"] = calories

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error searching recipes: {e}")
                return None

    async def get_recipe_by_uri(self, recipe_uri: str) -> Optional[Dict]:
        """
        Fetch a specific recipe by its URI or ID.
        Edamam IDs are often part of the URI, e.g., '.../recipe_id'
        """
        # Extract ID from URI if needed, or use the ID directly
        # The URI usually looks like: http://www.edamam.com/ontologies/edamam.owl#recipe_b79327d05b8e5b838ad6cfd9576b30b6
        # The API expects the hash part 'b79327d05b8e5b838ad6cfd9576b30b6'

        recipe_id = recipe_uri
        if "#recipe_" in recipe_uri:
            recipe_id = recipe_uri.split("#recipe_")[1]

        async with httpx.AsyncClient() as client:
            try:
                # We use the ID endpoint: /api/recipes/v2/{id}
                url = f"{self.BASE_URL}/{recipe_id}"

                response = await client.get(
                    url,
                    params={
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "type": "public"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error fetching recipe details: {e}")
                return None