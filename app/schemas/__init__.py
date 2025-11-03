"""
Pydantic Schemas for FreshMind API
Request and Response Models for validation and serialization
"""

from pydantic import BaseModel, Field, EmailStr, validator, UUID4
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# Export all schemas for easy importing
__all__ = [
    # Enums
    "StorageLocation",
    "DataSource",
    "FreshnessStatus",
    "GroceryReason",
    # User Schemas
    "UserBase",
    "UserCreate",
    "UserResponse",
    # Food Item Schemas
    "FoodItemBase",
    "FoodItemCreate",
    "FoodItemResponse",
    # Inventory Schemas
    "InventoryItemBase",
    "InventoryItemCreate",
    "InventoryItemUpdate",
    "InventoryItemResponse",
    "InventoryStatsResponse",
    # Barcode Schemas
    "BarcodeScanRequest",
    "BarcodeScanResponse",
]


# Enums
class StorageLocation(str, Enum):
    FRIDGE = "fridge"
    FREEZER = "freezer"
    PANTRY = "pantry"
    COUNTER = "counter"


class DataSource(str, Enum):
    OPENFOODFACTS = "openfoodfacts"
    USDA = "usda"
    EDAMAM = "edamam"
    USER_CUSTOM = "user_custom"


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    CONSUME_SOON = "consume_soon"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


class GroceryReason(str, Enum):
    DONT_HAVE = "dont_have"
    EXPIRING_SOON = "expiring_soon"
    NEED_MORE = "need_more"
    RECIPE_REQUIREMENT = "recipe_requirement"


# User Schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    unit_preference: str = "metric"


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    user_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Food Item Schemas
class FoodItemBase(BaseModel):
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    barcode: Optional[str] = None


class FoodItemCreate(FoodItemBase):
    calories_per_100g: Optional[Decimal] = None
    protein_per_100g: Optional[Decimal] = None
    carbs_per_100g: Optional[Decimal] = None
    fat_per_100g: Optional[Decimal] = None
    fiber_per_100g: Optional[Decimal] = None
    is_vegan: bool = False
    is_vegetarian: bool = False
    is_gluten_free: bool = False
    is_dairy_free: bool = False
    is_halal: bool = False
    is_kosher: bool = False
    image_url: Optional[str] = None
    data_source: str = "user_custom"


class FoodItemResponse(FoodItemBase):
    food_id: UUID4
    calories_per_100g: Optional[Decimal]
    protein_per_100g: Optional[Decimal]
    carbs_per_100g: Optional[Decimal]
    fat_per_100g: Optional[Decimal]
    is_vegan: bool
    is_vegetarian: bool
    is_gluten_free: bool
    is_dairy_free: bool
    is_halal: bool
    is_kosher: bool
    data_source: Optional[str]
    image_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Inventory Schemas
class InventoryItemBase(BaseModel):
    quantity: Decimal = Field(..., gt=0)
    unit: str
    expiry_date: date
    storage_location: StorageLocation = StorageLocation.FRIDGE
    notes: Optional[str] = None


class InventoryItemCreate(InventoryItemBase):
    food_id: Optional[UUID4] = None
    barcode: Optional[str] = None
    purchase_date: Optional[date] = None
    production_date: Optional[date] = None
    price_paid: Optional[Decimal] = None
    currency: str = "USD"


class InventoryItemUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = None
    expiry_date: Optional[date] = None
    storage_location: Optional[StorageLocation] = None
    notes: Optional[str] = None


class InventoryItemResponse(InventoryItemBase):
    inventory_id: UUID4
    user_id: UUID4
    food_id: UUID4
    purchase_date: Optional[date]
    price_paid: Optional[Decimal]
    currency: str
    freshness_status: str
    days_until_expiry: Optional[int]
    food_name: str
    food_category: Optional[str]
    food_image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryStatsResponse(BaseModel):
    total_items: int
    total_value: Optional[Decimal]
    fresh_count: int
    consume_soon_count: int
    expiring_soon_count: int
    expired_count: int
    categories: dict
    storage_breakdown: dict


class BarcodeScanRequest(BaseModel):
    barcode: str = Field(..., min_length=8, max_length=50)


class BarcodeScanResponse(BaseModel):
    found: bool
    food_item: Optional[FoodItemResponse] = None
    message: Optional[str] = None


# Request schemas
class RecipeIngredientCreate(BaseModel):
    food_id: UUID4
    quantity: float
    unit: str
    ingredient_note: Optional[str] = None
    is_optional: bool = False
    display_order: Optional[int] = None


class RecipeCreate(BaseModel):
    recipe_name: str
    description: Optional[str] = None
    cuisine_type: Optional[str] = None
    meal_type: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    servings: int = 1
    instructions: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None

    # Dietary flags
    is_vegan: bool = False
    is_vegetarian: bool = False
    is_gluten_free: bool = False
    is_dairy_free: bool = False
    is_halal: bool = False
    is_kosher: bool = False
    is_low_carb: bool = False
    is_high_protein: bool = False

    difficulty_level: Optional[str] = None
    spiciness_level: Optional[int] = Field(None, ge=0, le=5)

    ingredients: List[RecipeIngredientCreate]
    allergen_ids: Optional[List[int]] = []


class RecipeUpdate(BaseModel):
    recipe_name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    # ... other optional fields


# Response schemas
class RecipeIngredientResponse(BaseModel):
    recipe_ingredient_id: UUID4
    food_id: UUID4
    food_name: str  # Joined from food_items_master
    quantity: float
    unit: str
    ingredient_note: Optional[str]
    is_optional: bool
    display_order: Optional[int]

    class Config:
        from_attributes = True


class RecipeResponse(BaseModel):
    recipe_id: UUID4
    recipe_name: str
    description: Optional[str]
    cuisine_type: Optional[str]
    meal_type: Optional[str]

    prep_time_minutes: Optional[int]
    cook_time_minutes: Optional[int]
    total_time_minutes: Optional[int]
    servings: int

    instructions: Optional[str]
    source_url: Optional[str]
    image_url: Optional[str]

    # Nutritional data
    calories_per_serving: Optional[float]
    protein_per_serving: Optional[float]
    carbs_per_serving: Optional[float]
    fat_per_serving: Optional[float]

    # Dietary flags
    is_vegan: bool
    is_vegetarian: bool
    is_gluten_free: bool
    is_dairy_free: bool
    is_halal: bool
    is_kosher: bool
    is_low_carb: bool
    is_high_protein: bool

    difficulty_level: Optional[str]
    spiciness_level: Optional[int]

    data_source: str
    created_at: datetime

    # Relationships
    ingredients: List[RecipeIngredientResponse]
    allergens: List[str]  # List of allergen names

    class Config:
        from_attributes = True


class RecipeMatchScore(BaseModel):
    """For recommendation algorithm"""
    recipe: RecipeResponse
    match_score: float  # 0-100
    available_ingredients: int
    total_ingredients: int
    missing_ingredients: List[str]
# ============================================
# ALIASES AND MISSING SCHEMAS
# ============================================

# Aliases for backwards compatibility
BarcodeRequest = BarcodeScanRequest
BarcodeResponse = BarcodeScanResponse


class InventoryListResponse(BaseModel):
    """Response for list inventory endpoint with pagination metadata"""
    items: List[InventoryItemResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class SaveRecipeRequest(BaseModel):
    """Request to save/favorite a recipe"""
    notes: Optional[str] = Field(None, max_length=500, description="Personal notes about the recipe")