"""
Inventory management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
from uuid import UUID
from backend.app.services.usda import USDAService

from backend.app.database import get_db
from backend.app.models import UserInventory, FoodItemMaster
from backend.app.schemas import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    InventoryListResponse,
    InventoryStatsResponse,
    BarcodeRequest,
    BarcodeResponse,
    FoodItemResponse
)
from backend.app.services.openfoodfacts import OpenFoodFactsService

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
off_service = OpenFoodFactsService()
usda_service = USDAService()


def guess_food_image(name: str, category: Optional[str] = None) -> Optional[str]:
    """
    Assign a generic image based on the food name.
    Uses TheMealDB's free ingredient images.
    """
    name_lower = name.lower()

    # Map common keywords to image filenames
    # TheMealDB format: https://www.themealdb.com/images/ingredients/{Name}.png
    common_items = {
        "chicken": "Chicken",
        "rice": "Rice",
        "beef": "Beef",
        "pork": "Pork",
        "egg": "Eggs",
        "milk": "Milk",
        "cheese": "Cheese",
        "butter": "Butter",
        "apple": "Apple",
        "banana": "Banana",
        "orange": "Orange",
        "tomato": "Tomato",
        "potato": "Potatoes",
        "onion": "Onion",
        "carrot": "Carrots",
        "broccoli": "Broccoli",
        "bread": "Bread",
        "pasta": "Farfalle",  # Generic pasta
        "spaghetti": "Spaghetti",
        "fish": "Fish",
        "salmon": "Salmon",
        "tuna": "Tuna",
        "yogurt": "Greek Yogurt",
        "chocolate": "Chocolate",
        "flour": "Flour",
        "sugar": "Sugar",
        "salt": "Salt",
        "water": "Water",
        "oil": "Olive Oil",
        "avocado": "Avocado",
        "lettuce": "Lettuce",
        "cucumber": "Cucumber",
        "garlic": "Garlic",
        "lemon": "Lemon",
        "lime": "Lime",
        "strawberry": "Strawberries",
        "grape": "Grapes"
    }

    for key, filename in common_items.items():
        if key in name_lower:
            return f"https://www.themealdb.com/images/ingredients/{filename}.png"

    return None

# ==========================================
# 1. BARCODE SCANNING ( The Entry Point )
# ==========================================

@router.post("/scan", response_model=BarcodeResponse)
async def scan_barcode(
        barcode_data: BarcodeRequest,
        db: Session = Depends(get_db)
):
    """
    Scan a product barcode and fetch food information.
    Checks local DB first, then falls back to Open Food Facts API.
    """
    barcode = barcode_data.barcode
    
    # 1. Check local database first
    existing_food = db.query(FoodItemMaster).filter(FoodItemMaster.barcode == barcode).first()
    if existing_food:
        return BarcodeResponse(
            found=True,
            food_item=FoodItemResponse.from_orm(existing_food),
            message="Found in local database"
        )

    # 2. If not found, call Open Food Facts API
    product_data = await off_service.get_product_by_barcode(barcode)
    
    if not product_data:
        return BarcodeResponse(found=False, message="Product not found in global database")

    # 3. Parse API response and create new FoodItemMaster
    # Map nutritional values (handling potential missing keys)
    nutriments = product_data.get("nutrition", {})
    
    new_food = FoodItemMaster(
        barcode=barcode,
        name=product_data.get("name") or "Unknown Product",
        brand=product_data.get("brand"),
        image_url=product_data.get("image_url"),
        category=product_data.get("categories", [])[0] if product_data.get("categories") else "Unknown",
        
        # Nutrition Mapping
        calories_per_100g=nutriments.get("energy-kcal_100g"),
        protein_per_100g=nutriments.get("proteins_100g"),
        carbs_per_100g=nutriments.get("carbohydrates_100g"),
        fat_per_100g=nutriments.get("fat_100g"),
        fiber_per_100g=nutriments.get("fiber_100g"),
        sugar_per_100g=nutriments.get("sugars_100g"),
        sodium_per_100g=nutriments.get("sodium_100g"),
        
        # Dietary Flags (OpenFoodFacts logic)
        is_vegan=product_data.get("certifications", {}).get("vegan", False),
        is_vegetarian=product_data.get("certifications", {}).get("vegetarian", False),
        is_gluten_free=product_data.get("certifications", {}).get("gluten_free", False),
        
        data_source="openfoodfacts"
    )

    db.add(new_food)
    db.commit()
    db.refresh(new_food)

    return BarcodeResponse(
        found=True, 
        food_item=FoodItemResponse.from_orm(new_food),
        message="Fetched from Open Food Facts"
    )


# ==========================================
# 2. INVENTORY CRUD OPERATIONS
# ==========================================

@router.post("/items", response_model=InventoryItemResponse, status_code=201)
async def add_inventory_item(
        item: InventoryItemCreate,
        user_id: str = Query(..., description="User ID"),
        db: Session = Depends(get_db)
):
    """Add a new item to user's inventory"""

    # 1. VALIDATION: Check if user_id is a valid UUID format
    try:
        valid_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a UUID.")

    # 2. VALIDATION: Check if food_id exists
    if not item.food_id:
        raise HTTPException(status_code=400, detail="food_id is required")

    # We fetch this to check existence, but also to get the name/category/image for the response later
    food_item = db.query(FoodItemMaster).filter(FoodItemMaster.food_id == item.food_id).first()
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found. Did you scan it first?")

    # 3. ACTION: Create inventory record
    try:
        new_item = UserInventory(
            user_id=valid_user_id,
            food_id=item.food_id,
            quantity=item.quantity,
            unit=item.unit,
            expiry_date=item.expiry_date,
            storage_location=item.storage_location,
            purchase_date=item.purchase_date or date.today(),
            price_paid=item.price_paid,
            notes=item.notes
        )

        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        # 4. FIX: Construct response manually to satisfy Pydantic schema
        # We merge the inventory item data with the flattened food details
        return {
            "inventory_id": new_item.inventory_id,
            "user_id": new_item.user_id,
            "food_id": new_item.food_id,
            "quantity": new_item.quantity,
            "unit": new_item.unit,
            "expiry_date": new_item.expiry_date,
            "storage_location": new_item.storage_location,
            "notes": new_item.notes,
            "purchase_date": new_item.purchase_date,
            "price_paid": new_item.price_paid,
            "currency": new_item.currency,
            "created_at": new_item.created_at,
            "updated_at": new_item.updated_at,

            # These properties come from the hybrid_properties in UserInventory model
            "freshness_status": new_item.freshness_status,
            "days_until_expiry": new_item.days_until_expiry,

            # These are the MISSING fields that caused the error
            # We pull them from the food_item object we queried in step 2
            "food_name": food_item.name,
            "food_category": food_item.category,
            "food_image_url": food_item.image_url
        }

    except Exception as e:
        db.rollback()
        if "foreign key constraint" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found. Please create a user first.")
        print(f"Database error: {str(e)}")  # Print error to console for debugging
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/items", response_model=InventoryListResponse)
async def list_inventory_items(
        user_id: str,
        category: Optional[str] = None,
        storage_location: Optional[str] = None,
        freshness_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        db: Session = Depends(get_db)
):
    """Get all inventory items with filters and pagination"""

    # 1. Base Query joining FoodItemMaster for metadata
    # We use outerjoin to ensure we get the item even if food_item is missing (edge case)
    query = db.query(UserInventory).outerjoin(FoodItemMaster).filter(UserInventory.user_id == UUID(user_id))

    # 2. Apply Filters
    if storage_location:
        query = query.filter(UserInventory.storage_location == storage_location)

    if category:
        query = query.filter(FoodItemMaster.category.ilike(f"%{category}%"))

    if freshness_status:
        today = date.today()
        if freshness_status == "expired":
            query = query.filter(UserInventory.expiry_date < today)
        elif freshness_status == "expiring_soon":
            query = query.filter(UserInventory.expiry_date >= today,
                                 UserInventory.expiry_date <= today + timedelta(days=3))
        elif freshness_status == "consume_soon":
            query = query.filter(UserInventory.expiry_date >= today,
                                 UserInventory.expiry_date <= today + timedelta(days=7))
        elif freshness_status == "fresh":
            query = query.filter(UserInventory.expiry_date > today + timedelta(days=7))

    # 3. Pagination
    total_count = query.count()
    total_pages = (total_count + page_size - 1) // page_size

    # Fetch raw DB objects
    db_items = query.offset((page - 1) * page_size).limit(page_size).all()

    # 4. MANUAL MAPPING (Fixes the 500 Error)
    # Convert DB objects to dictionaries that match the Schema structure
    response_items = []
    for item in db_items:
        response_items.append({
            "inventory_id": item.inventory_id,
            "user_id": item.user_id,
            "food_id": item.food_id,
            "quantity": item.quantity,
            "unit": item.unit,
            "expiry_date": item.expiry_date,
            "storage_location": item.storage_location,
            "notes": item.notes,
            "purchase_date": item.purchase_date,
            "price_paid": item.price_paid,
            "currency": item.currency,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "freshness_status": item.freshness_status,
            "days_until_expiry": item.days_until_expiry,

            # Flatten the nested food_item fields
            "food_name": item.food_item.name if item.food_item else "Unknown",
            "food_category": item.food_item.category if item.food_item else None,
            "food_image_url": item.food_item.image_url if item.food_item else None
        })

    return InventoryListResponse(
        items=response_items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/items/{inventory_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
        inventory_id: str,
        user_id: str,
        db: Session = Depends(get_db)
):
    item = db.query(UserInventory).filter(
        UserInventory.inventory_id == UUID(inventory_id),
        UserInventory.user_id == UUID(user_id)
    ).join(FoodItemMaster).first()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.put("/items/{inventory_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
        inventory_id: str,
        updates: InventoryItemUpdate,
        user_id: str,
        db: Session = Depends(get_db)
):
    item = db.query(UserInventory).filter(
        UserInventory.inventory_id == UUID(inventory_id),
        UserInventory.user_id == UUID(user_id)
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Apply updates dynamically
    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{inventory_id}", status_code=204)
async def delete_inventory_item(
        inventory_id: str,
        user_id: str,
        db: Session = Depends(get_db)
):
    item = db.query(UserInventory).filter(
        UserInventory.inventory_id == UUID(inventory_id),
        UserInventory.user_id == UUID(user_id)
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    db.delete(item)
    db.commit()
    return


@router.get("/expiring", response_model=List[InventoryItemResponse])
async def get_expiring_items(
        user_id: str,
        days: int = 7,
        db: Session = Depends(get_db)
):
    """Get items expiring within the next N days"""
    today = date.today()
    limit_date = today + timedelta(days=days)

    items = db.query(UserInventory).filter(
        UserInventory.user_id == UUID(user_id),
        UserInventory.expiry_date >= today,
        UserInventory.expiry_date <= limit_date
    ).join(FoodItemMaster).order_by(UserInventory.expiry_date.asc()).all()

    return items


@router.get("/stats", response_model=InventoryStatsResponse)
async def get_inventory_stats(
        user_id: str,
        db: Session = Depends(get_db)
):
    """Get inventory statistics"""
    items = db.query(UserInventory).join(FoodItemMaster).filter(UserInventory.user_id == UUID(user_id)).all()
    
    stats = {
        "total_items": len(items),
        "total_value": sum(item.price_paid or 0 for item in items),
        "fresh_count": 0,
        "consume_soon_count": 0,
        "expiring_soon_count": 0,
        "expired_count": 0,
        "categories": {},
        "storage_breakdown": {}
    }

    # Aggregate data in python for simplicity
    for item in items:
        status = item.freshness_status
        if status == "fresh": stats["fresh_count"] += 1
        elif status == "consume_soon": stats["consume_soon_count"] += 1
        elif status == "expiring_soon": stats["expiring_soon_count"] += 1
        elif status == "expired": stats["expired_count"] += 1
        
        # Category count
        cat = item.food_item.category or "Uncategorized"
        stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
        
        # Storage count
        loc = item.storage_location
        stats["storage_breakdown"][loc] = stats["storage_breakdown"].get(loc, 0) + 1

    return stats


@router.get("/search", response_model=List[FoodItemResponse])
async def search_food_items(
        query: str,
        db: Session = Depends(get_db)
):
    """
    Search for food items by name.
    1. Search Local DB
    2. If few results, search USDA/OpenFoodFacts and save to local DB
    """
    # 1. Local Search
    local_results = db.query(FoodItemMaster).filter(
        FoodItemMaster.name.ilike(f"%{query}%")
    ).limit(5).all()

    results = [FoodItemResponse.from_orm(item) for item in local_results]

    # 2. External Search (if we have few local results)
    if len(results) < 5:
        usda_data = await usda_service.search_foods(query)
        if usda_data and 'foods' in usda_data:
            for food in usda_data['foods']:
                # Avoid duplicates by checking fdcId or name
                existing = db.query(FoodItemMaster).filter(FoodItemMaster.usda_fdc_id == food['fdcId']).first()
                if not existing:
                    image_url = guess_food_image(food['description'], food.get('foodCategory'))
                    # Parse USDA data to FoodItemMaster (Simplified for brevity)
                    new_food = FoodItemMaster(
                        name=food['description'],
                        category=food.get('foodCategory'),
                        usda_fdc_id=food['fdcId'],
                        data_source="usda",
                        image_url=image_url
                    )
                    db.add(new_food)
                    db.commit()
                    db.refresh(new_food)
                    results.append(FoodItemResponse.from_orm(new_food))

    return results