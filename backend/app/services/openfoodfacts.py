import httpx
from typing import Optional, Dict


class OpenFoodFactsService:
    """Service for interacting with Open Food Facts API"""
    BASE_URL = "https://world.openfoodfacts.org/api/v2"

    async def get_product_by_barcode(self, barcode: str) -> Optional[Dict]:
        """
        Scan barcode and get product information

        Args:
            barcode: Product barcode (UPC, EAN, etc.)

        Returns:
            Product information including name, ingredients, allergens, nutrition
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/product/{barcode}.json",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == 1:
                    product = data["product"]
                    return {
                        "barcode": barcode,
                        "name": product.get("product_name"),
                        "brand": product.get("brands"),
                        "ingredients": product.get("ingredients_text"),
                        "allergens": product.get("allergens_tags", []),
                        "nutrition": product.get("nutriments", {}),
                        "certifications": {
                            "halal": "en:halal" in product.get("labels_tags", []),
                            "kosher": "en:kosher" in product.get("labels_tags", []),
                            "vegan": "en:vegan" in product.get("labels_tags", []),
                            "vegetarian": "en:vegetarian" in product.get("labels_tags", []),
                            "gluten_free": "en:gluten-free" in product.get("labels_tags", []),
                        },
                        "image_url": product.get("image_url"),
                        "categories": product.get("categories_tags", []),
                    }
                return None
            except httpx.HTTPError as e:
                print(f"Error fetching product: {e}")
                return None