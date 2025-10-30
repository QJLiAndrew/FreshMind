import httpx
from typing import Optional, Dict, List
from app.database import get_settings

settings = get_settings()


class EdamamFoodService:
    """Service for Edamam Food Database API"""
    BASE_URL = "https://api.edamam.com/api/food-database/v2"

    def __init__(self):
        self.app_id = settings.edamam_food_app_id
        self.app_key = settings.edamam_food_app_key

    async def search_food(self, query: str) -> Optional[Dict]:
        """
        Search for food items and get nutritional data

        Args:
            query: Food name or ingredient

        Returns:
            Food search results with nutritional information
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/parser",
                    params={
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "ingr": query,
                        "nutrition-type": "logging"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error searching food: {e}")
                return None

    async def get_nutrients(self, ingredients: List[Dict]) -> Optional[Dict]:
        """
        Get detailed nutritional breakdown for ingredients

        Args:
            ingredients: List of ingredients with quantity and foodId

        Returns:
            Detailed nutritional information
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/nutrients",
                    params={
                        "app_id": self.app_id,
                        "app_key": self.app_key
                    },
                    json={"ingredients": ingredients},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error getting nutrients: {e}")
                return None


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
        """
        Search for recipes with filters

        Args:
            query: Ingredients or recipe name
            diet: Diet label (e.g., balanced, high-protein, low-carb)
            health: Health labels (e.g., vegan, vegetarian, gluten-free, kosher, halal)
            cuisine_type: Cuisine type (e.g., Italian, Asian, Mexican)
            meal_type: Meal type (e.g., breakfast, lunch, dinner, snack)
            calories: Calorie range (e.g., "100-500")

        Returns:
            Recipe search results
        """
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "q": query,
            "type": "public"
        }

        if diet:
            params["diet"] = diet
        if health:
            params["health"] = health
        if cuisine_type:
            params["cuisineType"] = cuisine_type
        if meal_type:
            params["mealType"] = meal_type
        if calories:
            params["calories"] = calories

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