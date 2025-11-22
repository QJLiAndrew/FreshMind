from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from backend.app.database import get_db
from backend.app.models import UserGroceryList, UserInventory, RecipeMaster

# Define a simple Pydantic schema for response here to keep it self-contained
# (In a real app, you'd put this in schemas/__init__.py)
from pydantic import BaseModel
from datetime import datetime, date, timedelta


class GroceryItemResponse(BaseModel):
    grocery_item_id: UUID
    food_name: str
    quantity_needed: float
    unit: str
    is_purchased: bool
    reason: Optional[str]
    associated_recipe_name: Optional[str] = None

    class Config:
        from_attributes = True


class GroceryItemCreate(BaseModel):
    food_id: UUID
    quantity: float
    unit: str
    reason: str = "manual_add"


router = APIRouter(prefix="/api/grocery", tags=["grocery"])


# ==========================================
# 1. LIST & MANAGE ITEMS
# ==========================================

@router.get("/", response_model=List[GroceryItemResponse])
async def get_grocery_list(
        user_id: str,
        show_purchased: bool = False,
        db: Session = Depends(get_db)
):
    """Get user's grocery list"""
    query = db.query(UserGroceryList).filter(UserGroceryList.user_id == UUID(user_id))

    if not show_purchased:
        query = query.filter(UserGroceryList.is_purchased == False)

    items = query.options(
        joinedload(UserGroceryList.food_item),
        joinedload(UserGroceryList.associated_recipe)
    ).all()

    # Manual mapping to flat response
    response = []
    for item in items:
        response.append({
            "grocery_item_id": item.grocery_item_id,
            "food_name": item.food_item.name if item.food_item else "Unknown",
            "quantity_needed": float(item.quantity_needed),
            "unit": item.unit,
            "is_purchased": item.is_purchased,
            "reason": item.reason,
            "associated_recipe_name": item.associated_recipe.recipe_name if item.associated_recipe else None
        })

    return response


@router.post("/items", status_code=201)
async def add_manual_item(
        item: GroceryItemCreate,
        user_id: str = Query(...),
        db: Session = Depends(get_db)
):
    """Manually add an item to the list"""
    new_item = UserGroceryList(
        user_id=UUID(user_id),
        food_id=item.food_id,
        quantity_needed=item.quantity,
        unit=item.unit,
        reason=item.reason,
        is_purchased=False
    )
    db.add(new_item)
    db.commit()
    return {"status": "added", "id": str(new_item.grocery_item_id)}


@router.put("/{item_id}/toggle", status_code=200)
async def toggle_purchased_status(
        item_id: str,
        user_id: str = Query(...),
        db: Session = Depends(get_db)
):
    """Mark item as purchased/unpurchased"""
    item = db.query(UserGroceryList).filter(
        UserGroceryList.grocery_item_id == UUID(item_id),
        UserGroceryList.user_id == UUID(user_id)
    ).first()

    if not item:
        raise HTTPException(404, "Item not found")

    item.is_purchased = not item.is_purchased
    db.commit()
    return {"status": "updated", "is_purchased": item.is_purchased}


@router.delete("/purchased", status_code=204)
async def clear_purchased_items(
        user_id: str = Query(...),
        db: Session = Depends(get_db)
):
    """Clear all bought items from the list"""
    db.query(UserGroceryList).filter(
        UserGroceryList.user_id == UUID(user_id),
        UserGroceryList.is_purchased == True
    ).delete()
    db.commit()


@router.post("/checkout", status_code=200)
async def checkout_grocery_list(
        user_id: str = Query(...),
        db: Session = Depends(get_db)
):
    """
    Move purchased items from Grocery List -> User Inventory
    Then clear them from the list.
    """
    # 1. Find purchased items
    purchased_items = db.query(UserGroceryList).filter(
        UserGroceryList.user_id == UUID(user_id),
        UserGroceryList.is_purchased == True
    ).all()

    if not purchased_items:
        raise HTTPException(status_code=400, detail="No purchased items to checkout")

    moved_count = 0

    # 2. Move to Inventory
    for item in purchased_items:
        # Create inventory entry
        new_inventory = UserInventory(
            user_id=item.user_id,
            food_id=item.food_id,
            quantity=item.quantity_needed,
            unit=item.unit,
            # Default expiry: 1 week from now (MVP logic)
            expiry_date=date.today() + timedelta(days=7),
            storage_location="fridge",
            notes=f"Bought from grocery list on {date.today()}"
        )
        db.add(new_inventory)

        # Delete from grocery list
        db.delete(item)
        moved_count += 1

    db.commit()

    return {"message": f"Successfully moved {moved_count} items to your fridge!"}


# ==========================================
# 2. SMART GENERATION (The "Brain")
# ==========================================

@router.post("/generate/{recipe_id}")
async def generate_from_recipe(
        recipe_id: str,
        user_id: str = Query(...),
        db: Session = Depends(get_db)
):
    """
    Compare Recipe Ingredients vs. User Inventory.
    Add missing items to Grocery List.
    """
    # 1. Fetch Recipe
    recipe = db.query(RecipeMaster).filter(RecipeMaster.recipe_id == UUID(recipe_id)).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    # 2. Fetch User's Inventory for relevant foods
    # Get all food_ids used in this recipe
    recipe_food_ids = [ing.food_id for ing in recipe.ingredients]

    inventory_items = db.query(UserInventory).filter(
        UserInventory.user_id == UUID(user_id),
        UserInventory.food_id.in_(recipe_food_ids),
        UserInventory.expiry_date >= datetime.now().date()  # Only count fresh items
    ).all()

    # Map food_id -> total quantity available
    inventory_map = {}
    for item in inventory_items:
        fid = str(item.food_id)
        inventory_map[fid] = inventory_map.get(fid, 0) + float(item.quantity)

    # 3. Calculate Deficits
    added_items = []

    for ing in recipe.ingredients:
        food_id_str = str(ing.food_id)
        required_qty = float(ing.quantity)
        available_qty = inventory_map.get(food_id_str, 0)

        if available_qty < required_qty:
            missing_qty = required_qty - available_qty

            # Check if already on grocery list to avoid duplicates
            existing = db.query(UserGroceryList).filter(
                UserGroceryList.user_id == UUID(user_id),
                UserGroceryList.food_id == ing.food_id,
                UserGroceryList.is_purchased == False
            ).first()

            if existing:
                # Update existing request
                existing.quantity_needed = float(existing.quantity_needed) + missing_qty
            else:
                # Add new request
                new_grocery_item = UserGroceryList(
                    user_id=UUID(user_id),
                    food_id=ing.food_id,
                    quantity_needed=missing_qty,
                    unit=ing.unit,
                    reason="recipe_requirement",
                    associated_recipe_id=recipe.recipe_id
                )
                db.add(new_grocery_item)
                added_items.append(ing.food_item.name)

    db.commit()

    return {
        "message": "Grocery list updated",
        "items_added": added_items,
        "recipe_name": recipe.recipe_name
    }