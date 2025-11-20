"""
SQLAlchemy Models for FreshMind Application
Matches the PostgreSQL schema defined in create_database.sql
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, Date, DateTime,
    ForeignKey, CheckConstraint, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, date
import uuid

from backend.app.database import Base


# ============================================
# 1. USERS MODEL
# ============================================
# ============================================
# 1. USERS MODEL (Updated with Dietary Profile)
# ============================================
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    unit_preference = Column(String(10), default='metric')

    # --- NEW: Dietary Preferences ---
    is_vegan = Column(Boolean, default=False)
    is_vegetarian = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    is_dairy_free = Column(Boolean, default=False)
    is_halal = Column(Boolean, default=False)
    is_kosher = Column(Boolean, default=False)

    # --- NEW: Nutritional Goals (Daily) ---
    daily_calorie_goal = Column(Integer, default=2000)
    daily_protein_goal = Column(Integer, default=50)  # grams

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_items = relationship("UserInventory", back_populates="user", cascade="all, delete-orphan")
    grocery_items = relationship("UserGroceryList", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


# ============================================
# 2. FOOD ITEMS MASTER MODEL
# ============================================
class FoodItemMaster(Base):
    __tablename__ = "food_items_master"

    food_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identifiers
    barcode = Column(String(50), unique=True, index=True)
    usda_fdc_id = Column(Integer, unique=True)
    edamam_food_id = Column(String(100), unique=True)

    # Basic Info
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(255))
    category = Column(String(100), index=True)

    # Nutritional Data (per 100g)
    calories_per_100g = Column(DECIMAL(10, 2))
    protein_per_100g = Column(DECIMAL(10, 2))
    carbs_per_100g = Column(DECIMAL(10, 2))
    fat_per_100g = Column(DECIMAL(10, 2))
    fiber_per_100g = Column(DECIMAL(10, 2))
    sugar_per_100g = Column(DECIMAL(10, 2))
    sodium_per_100g = Column(DECIMAL(10, 2))

    # Extended Nutrition
    vitamin_a_per_100g = Column(DECIMAL(10, 2))
    vitamin_c_per_100g = Column(DECIMAL(10, 2))
    vitamin_d_per_100g = Column(DECIMAL(10, 2))
    calcium_per_100g = Column(DECIMAL(10, 2))
    iron_per_100g = Column(DECIMAL(10, 2))

    # Serving Information
    serving_size_g = Column(DECIMAL(10, 2))
    serving_size_description = Column(String(100))

    # Dietary Flags
    is_vegan = Column(Boolean, default=False)
    is_vegetarian = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    is_dairy_free = Column(Boolean, default=False)
    is_halal = Column(Boolean, default=False)
    is_kosher = Column(Boolean, default=False)
    is_organic = Column(Boolean, default=False)

    # Product Info
    image_url = Column(Text)
    data_source = Column(String(50))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "data_source IN ('openfoodfacts', 'usda', 'edamam', 'user_custom')",
            name='check_data_source'
        ),
    )

    # Relationships
    allergens = relationship("FoodItemAllergen", back_populates="food_item", cascade="all, delete-orphan")
    inventory_entries = relationship("UserInventory", back_populates="food_item")
    recipe_uses = relationship("RecipeIngredient", back_populates="food_item")
    grocery_entries = relationship("UserGroceryList", back_populates="food_item")

    def __repr__(self):
        return f"<FoodItemMaster(name='{self.name}', category='{self.category}')>"

    @hybrid_property
    def calories_per_serving(self):
        """Calculate calories per serving if serving_size_g is available"""
        if self.serving_size_g and self.calories_per_100g:
            return (self.calories_per_100g * self.serving_size_g) / 100
        return None


# ============================================
# 3. ALLERGENS MODEL
# ============================================
class Allergen(Base):
    __tablename__ = "allergens"

    allergen_id = Column(Integer, primary_key=True, autoincrement=True)
    allergen_name = Column(String(100), unique=True, nullable=False)
    allergen_group = Column(String(50))

    # Relationships
    food_items = relationship("FoodItemAllergen", back_populates="allergen")
    recipes = relationship("RecipeAllergen", back_populates="allergen")

    def __repr__(self):
        return f"<Allergen(name='{self.allergen_name}', group='{self.allergen_group}')>"


# ============================================
# 4. FOOD ITEM ALLERGENS MODEL (Junction Table)
# ============================================
class FoodItemAllergen(Base):
    __tablename__ = "food_item_allergens"

    food_id = Column(UUID(as_uuid=True), ForeignKey('food_items_master.food_id', ondelete='CASCADE'), primary_key=True)
    allergen_id = Column(Integer, ForeignKey('allergens.allergen_id', ondelete='CASCADE'), primary_key=True)
    allergen_type = Column(String(20), default='contains')  # 'contains' or 'may_contain'

    # Relationships
    food_item = relationship("FoodItemMaster", back_populates="allergens")
    allergen = relationship("Allergen", back_populates="food_items")

    def __repr__(self):
        return f"<FoodItemAllergen(food_id='{self.food_id}', allergen_id={self.allergen_id})>"


# ============================================
# 5. USER INVENTORY MODEL
# ============================================
class UserInventory(Base):
    __tablename__ = "user_inventory"

    inventory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    food_id = Column(UUID(as_uuid=True), ForeignKey('food_items_master.food_id', ondelete='CASCADE'), nullable=False, index=True)

    # User-Specific Data
    quantity = Column(DECIMAL(10, 2), nullable=False)
    unit = Column(String(20), nullable=False)

    # Dates
    purchase_date = Column(Date)
    production_date = Column(Date)
    expiry_date = Column(Date, nullable=False, index=True)

    # Storage
    storage_location = Column(String(50), default='fridge')

    # Cost Tracking
    price_paid = Column(DECIMAL(10, 2))
    currency = Column(String(3), default='USD')

    # Notes
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint(
            "storage_location IN ('fridge', 'freezer', 'pantry', 'counter')",
            name='check_storage_location'
        ),
    )

    # Relationships
    user = relationship("User", back_populates="inventory_items")
    food_item = relationship("FoodItemMaster", back_populates="inventory_entries")

    def __repr__(self):
        return f"<UserInventory(food='{self.food_item.name if self.food_item else 'N/A'}', quantity={self.quantity}, expiry={self.expiry_date})>"

    @hybrid_property
    def freshness_status(self):
        """Calculate freshness status based on expiry date"""
        if not self.expiry_date:
            return 'unknown'

        today = date.today()
        days_until_expiry = (self.expiry_date - today).days

        if days_until_expiry < 0:
            return 'expired'
        elif days_until_expiry <= 3:
            return 'expiring_soon'
        elif days_until_expiry <= 7:
            return 'consume_soon'
        else:
            return 'fresh'

    @hybrid_property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def is_expired(self):
        """Check if item is expired"""
        return self.expiry_date < date.today() if self.expiry_date else False


# ============================================
# 6. RECIPES MASTER MODEL
# ============================================
class RecipeMaster(Base):
    __tablename__ = "recipes_master"

    recipe_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identifiers
    edamam_recipe_uri = Column(String(255), unique=True)

    # Basic Info
    recipe_name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    cuisine_type = Column(String(100), index=True)
    meal_type = Column(String(50), index=True)

    # Timing
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    total_time_minutes = Column(Integer)

    # Servings
    servings = Column(Integer, nullable=False, default=1)

    # Instructions
    instructions = Column(Text)
    source_url = Column(Text)

    # Media
    image_url = Column(Text)

    # Nutritional Data (Total)
    total_calories = Column(DECIMAL(10, 2))
    total_protein = Column(DECIMAL(10, 2))
    total_carbs = Column(DECIMAL(10, 2))
    total_fat = Column(DECIMAL(10, 2))
    total_fiber = Column(DECIMAL(10, 2))

    # Per Serving
    calories_per_serving = Column(DECIMAL(10, 2))
    protein_per_serving = Column(DECIMAL(10, 2))
    carbs_per_serving = Column(DECIMAL(10, 2))
    fat_per_serving = Column(DECIMAL(10, 2))

    # Dietary Flags
    is_vegan = Column(Boolean, default=False)
    is_vegetarian = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    is_dairy_free = Column(Boolean, default=False)
    is_halal = Column(Boolean, default=False)
    is_kosher = Column(Boolean, default=False)
    is_low_carb = Column(Boolean, default=False)
    is_high_protein = Column(Boolean, default=False)

    # Difficulty & Spiciness
    difficulty_level = Column(String(20))
    spiciness_level = Column(Integer)

    # Metadata
    data_source = Column(String(50), default='edamam')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint('spiciness_level BETWEEN 0 AND 5', name='check_spiciness_level'),
        CheckConstraint(
            "data_source IN ('edamam', 'user_custom')",
            name='check_data_source_recipe'
        ),
    )

    # Relationships
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    allergens = relationship("RecipeAllergen", back_populates="recipe", cascade="all, delete-orphan")
    grocery_entries = relationship("UserGroceryList", back_populates="associated_recipe")

    def __repr__(self):
        return f"<RecipeMaster(name='{self.recipe_name}', cuisine='{self.cuisine_type}')>"


# ============================================
# 7. RECIPE INGREDIENTS MODEL
# ============================================
class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    recipe_ingredient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes_master.recipe_id', ondelete='CASCADE'), nullable=False, index=True)
    food_id = Column(UUID(as_uuid=True), ForeignKey('food_items_master.food_id', ondelete='CASCADE'), nullable=False, index=True)

    # Ingredient Details
    quantity = Column(DECIMAL(10, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    ingredient_note = Column(String(255))

    # Flags
    is_optional = Column(Boolean, default=False)
    display_order = Column(Integer)

    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive_ingredient'),
    )

    # Relationships
    recipe = relationship("RecipeMaster", back_populates="ingredients")
    food_item = relationship("FoodItemMaster", back_populates="recipe_uses")

    def __repr__(self):
        return f"<RecipeIngredient(recipe='{self.recipe.recipe_name if self.recipe else 'N/A'}', food='{self.food_item.name if self.food_item else 'N/A'}')>"


# ============================================
# 8. RECIPE ALLERGENS MODEL (Junction Table)
# ============================================
class RecipeAllergen(Base):
    __tablename__ = "recipe_allergens"

    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes_master.recipe_id', ondelete='CASCADE'), primary_key=True)
    allergen_id = Column(Integer, ForeignKey('allergens.allergen_id', ondelete='CASCADE'), primary_key=True)

    # Relationships
    recipe = relationship("RecipeMaster", back_populates="allergens")
    allergen = relationship("Allergen", back_populates="recipes")

    def __repr__(self):
        return f"<RecipeAllergen(recipe_id='{self.recipe_id}', allergen_id={self.allergen_id})>"


# ============================================
# 9. USER GROCERY LIST MODEL
# ============================================
class UserGroceryList(Base):
    __tablename__ = "user_grocery_list"

    grocery_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    food_id = Column(UUID(as_uuid=True), ForeignKey('food_items_master.food_id', ondelete='CASCADE'), nullable=False, index=True)

    # Item Details
    quantity_needed = Column(DECIMAL(10, 2), nullable=False)
    unit = Column(String(20), nullable=False)

    # Context
    reason = Column(String(50))
    associated_recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes_master.recipe_id', ondelete='SET NULL'))

    # Current Inventory
    current_quantity = Column(DECIMAL(10, 2), default=0)
    quantity_to_buy = Column(DECIMAL(10, 2))

    # Shopping Info
    priority = Column(Integer, default=1, index=True)
    estimated_price = Column(DECIMAL(10, 2))
    store_preference = Column(String(100))
    aisle_location = Column(String(50))

    # Status
    is_purchased = Column(Boolean, default=False, index=True)
    purchased_date = Column(DateTime)

    # Notes
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "reason IN ('dont_have', 'expiring_soon', 'need_more', 'recipe_requirement')",
            name='check_reason'
        ),
    )

    # Relationships
    user = relationship("User", back_populates="grocery_items")
    food_item = relationship("FoodItemMaster", back_populates="grocery_entries")
    associated_recipe = relationship("RecipeMaster", back_populates="grocery_entries")

    def __repr__(self):
        return f"<UserGroceryList(food='{self.food_item.name if self.food_item else 'N/A'}', quantity={self.quantity_needed}, purchased={self.is_purchased})>"

    @property
    def needs_purchase(self):
        """Check if item needs to be purchased"""
        return not self.is_purchased and (self.quantity_to_buy or 0) > 0