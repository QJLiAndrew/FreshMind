"""
Pydantic schemas for inventory management endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class InventoryItemBase(BaseModel):
    """Base schema for inventory items"""
    food_id: str
    quantity: Decimal = Field(gt=0, description="Quantity must be positive")
    unit: str
    purchase_date: Optional[date] = None
    production_date: Optional[date] = None
    expiry_date: date
    storage_location: str = Field(default="fridge")
    price_paid: Optional[Decimal] = None
    currency: str = Field(default="USD")
    notes: Optional[str] = None

    @validator('storage_location')
    def validate_storage_location(cls, v):
        allowed = ['fridge', 'freezer', 'pantry', 'counter']
        if v not in allowed:
            raise ValueError(f'storage_location must be one of: {allowed}')
        return v


class InventoryItemCreate(InventoryItemBase):
    """Schema for creating a new inventory item"""
    pass


class InventoryItemUpdate(BaseModel):
    """Schema for updating an existing inventory item"""
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = None
    expiry_date: Optional[date] = None
    storage_location: Optional[str] = None
    price_paid: Optional[Decimal] = None
    notes: Optional[str] = None

    @validator('storage_location')
    def validate_storage_location(cls, v):
        if v is not None:
            allowed = ['fridge', 'freezer', 'pantry', 'counter']
            if v not in allowed:
                raise ValueError(f'storage_location must be one of: {allowed}')
        return v


class FoodItemInfo(BaseModel):
    """Basic food item information"""
    food_id: str
    name: str
    brand: Optional[str]
    category: Optional[str]
    image_url: Optional[str]

    class Config:
        from_attributes = True


class InventoryItemResponse(InventoryItemBase):
    """Schema for inventory item response"""
    inventory_id: str
    user_id: str
    freshness_status: str
    food_item: FoodItemInfo
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    """Schema for list of inventory items with metadata"""
    items: List[InventoryItemResponse]
    total_count: int
    page: int
    page_size: int
    filters_applied: dict


class InventoryStatsResponse(BaseModel):
    """Schema for inventory statistics"""
    total_items: int
    by_category: dict
    by_storage: dict
    by_freshness: dict
    total_value: Decimal
    expiring_soon_count: int
    expired_count: int


class BarcodeRequest(BaseModel):
    """Schema for barcode scanning request"""
    barcode: str = Field(..., description="Product barcode (EAN-13, UPC, etc)")


class BarcodeResponse(BaseModel):
    """Schema for barcode scanning response"""
    success: bool
    food_item: Optional[FoodItemInfo]
    message: Optional[str]