import httpx
from app.models import FoodItemMaster
from decimal import Decimal


async def scan_barcode(barcode: str) -> FoodItemMaster:
    """Scan barcode and get food item from Open Food Facts"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        )
        data = response.json()

        if data.get("status") != 1:
            return None

        product = data["product"]

        # Create FoodItemMaster from API data
        food_item = FoodItemMaster(
            name=product.get("product_name"),
            brand=product.get("brands"),
            barcode=barcode,
            # ... map more fields
            data_source="openfoodfacts"
        )
        return food_item