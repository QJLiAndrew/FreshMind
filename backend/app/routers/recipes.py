"""
Recipe management API endpoints

This module provides endpoints for:
- CRUD operations on recipes
- Smart recipe recommendations based on inventory
- Nutrition-based recipe filtering
- Edamam API integration for importing recipes
- User recipe management (save/favorite)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import timedelta
from datetime import date as date_type

from backend.app.database import get_db
from backend.app.schemas import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeMatchScore,
    SaveRecipeRequest
)

from backend.app.services.edamam import EdamamRecipeService
from uuid import UUID

router = APIRouter(prefix="/api/recipes", tags=["recipes"])
edamam_service = EdamamRecipeService()

"""
Helper functions for recipe router
"""

from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from backend.app.models import (
    RecipeIngredient, RecipeMaster, Allergen, RecipeAllergen,
    UserInventory, FoodItemMaster, User
)


def calculate_recipe_nutrition(ingredients: list, servings: int) -> dict:
    """
    Calculate total and per-serving nutritional values from ingredients

    Args:
        ingredients: List of RecipeIngredient objects with food_item loaded
        servings: Number of servings in the recipe

    Returns:
        Dictionary with total and per-serving nutritional values
    """
    total_calories = Decimal(0)
    total_protein = Decimal(0)
    total_carbs = Decimal(0)
    total_fat = Decimal(0)
    total_fiber = Decimal(0)

    for ingredient in ingredients:
        food = ingredient.food_item

        # Assume quantity is in grams (you may need unit conversion logic)
        quantity_in_100g = Decimal(ingredient.quantity) / Decimal(100)

        if food.calories_per_100g:
            total_calories += Decimal(food.calories_per_100g) * quantity_in_100g
        if food.protein_per_100g:
            total_protein += Decimal(food.protein_per_100g) * quantity_in_100g
        if food.carbs_per_100g:
            total_carbs += Decimal(food.carbs_per_100g) * quantity_in_100g
        if food.fat_per_100g:
            total_fat += Decimal(food.fat_per_100g) * quantity_in_100g
        if food.fiber_per_100g:
            total_fiber += Decimal(food.fiber_per_100g) * quantity_in_100g

    # Calculate per serving
    servings_decimal = Decimal(servings) if servings > 0 else Decimal(1)

    return {
        'total_calories': total_calories,
        'total_protein': total_protein,
        'total_carbs': total_carbs,
        'total_fat': total_fat,
        'total_fiber': total_fiber,
        'calories_per_serving': total_calories / servings_decimal,
        'protein_per_serving': total_protein / servings_decimal,
        'carbs_per_serving': total_carbs / servings_decimal,
        'fat_per_serving': total_fat / servings_decimal,
    }


def format_recipe_response(recipe: RecipeMaster, db: Session) -> dict:
    """
    Format a RecipeMaster model into a response dictionary

    Args:
        recipe: RecipeMaster object with ingredients and allergens loaded
        db: Database session

    Returns:
        Dictionary formatted for RecipeResponse schema
    """
    # Format ingredients
    ingredients = []
    for ing in recipe.ingredients:
        ingredients.append({
            'recipe_ingredient_id': str(ing.recipe_ingredient_id),
            'food_id': str(ing.food_id),
            'food_name': ing.food_item.name,
            'quantity': float(ing.quantity),
            'unit': ing.unit,
            'ingredient_note': ing.ingredient_note,
            'is_optional': ing.is_optional,
            'display_order': ing.display_order
        })

    # Get allergen names
    allergen_names = []
    for ra in recipe.allergens:
        allergen = db.query(Allergen.allergen_name).filter(
            Allergen.allergen_id == ra.allergen_id
        ).scalar()
        if allergen:
            allergen_names.append(allergen)

    return {
        'recipe_id': str(recipe.recipe_id),
        'recipe_name': recipe.recipe_name,
        'description': recipe.description,
        'cuisine_type': recipe.cuisine_type,
        'meal_type': recipe.meal_type,
        'prep_time_minutes': recipe.prep_time_minutes,
        'cook_time_minutes': recipe.cook_time_minutes,
        'total_time_minutes': recipe.total_time_minutes,
        'servings': recipe.servings,
        'instructions': recipe.instructions,
        'source_url': recipe.source_url,
        'image_url': recipe.image_url,
        'calories_per_serving': float(recipe.calories_per_serving) if recipe.calories_per_serving else None,
        'protein_per_serving': float(recipe.protein_per_serving) if recipe.protein_per_serving else None,
        'carbs_per_serving': float(recipe.carbs_per_serving) if recipe.carbs_per_serving else None,
        'fat_per_serving': float(recipe.fat_per_serving) if recipe.fat_per_serving else None,
        'is_vegan': recipe.is_vegan,
        'is_vegetarian': recipe.is_vegetarian,
        'is_gluten_free': recipe.is_gluten_free,
        'is_dairy_free': recipe.is_dairy_free,
        'is_halal': recipe.is_halal,
        'is_kosher': recipe.is_kosher,
        'is_low_carb': recipe.is_low_carb,
        'is_high_protein': recipe.is_high_protein,
        'difficulty_level': recipe.difficulty_level,
        'spiciness_level': recipe.spiciness_level,
        'data_source': recipe.data_source,
        'created_at': recipe.created_at,
        'ingredients': ingredients,
        'allergens': allergen_names
    }


# ============================================
# CORE CRUD OPERATIONS
# ============================================

@router.post("/", response_model=RecipeResponse, status_code=201)
async def create_recipe(
        recipe: RecipeCreate,
        user_id: str = Query(..., description="User ID creating the recipe"),
        db: Session = Depends(get_db)
):
    """Create a custom recipe"""

    # Validate all ingredient food_ids exist
    for ingredient in recipe.ingredients:
        food_item = db.query(FoodItemMaster).filter(
            FoodItemMaster.food_id == ingredient.food_id
        ).first()
        if not food_item:
            raise HTTPException(
                status_code=404,
                detail=f"Food item with ID {ingredient.food_id} not found"
            )

    # Calculate total time
    total_time = (recipe.prep_time_minutes or 0) + (recipe.cook_time_minutes or 0)

    # Create recipe
    new_recipe = RecipeMaster(
        recipe_name=recipe.recipe_name,
        description=recipe.description,
        cuisine_type=recipe.cuisine_type,
        meal_type=recipe.meal_type,
        prep_time_minutes=recipe.prep_time_minutes,
        cook_time_minutes=recipe.cook_time_minutes,
        total_time_minutes=total_time if total_time > 0 else None,
        servings=recipe.servings,
        instructions=recipe.instructions,
        source_url=recipe.source_url,
        image_url=recipe.image_url,
        is_vegan=recipe.is_vegan,
        is_vegetarian=recipe.is_vegetarian,
        is_gluten_free=recipe.is_gluten_free,
        is_dairy_free=recipe.is_dairy_free,
        is_halal=recipe.is_halal,
        is_kosher=recipe.is_kosher,
        is_low_carb=recipe.is_low_carb,
        is_high_protein=recipe.is_high_protein,
        difficulty_level=recipe.difficulty_level,
        spiciness_level=recipe.spiciness_level,
        data_source='user_custom'
    )

    db.add(new_recipe)
    db.flush()

    # Create ingredients
    ingredient_models = []
    for idx, ingredient in enumerate(recipe.ingredients):
        recipe_ingredient = RecipeIngredient(
            recipe_id=new_recipe.recipe_id,
            food_id=ingredient.food_id,
            quantity=ingredient.quantity,
            unit=ingredient.unit,
            ingredient_note=ingredient.ingredient_note,
            is_optional=ingredient.is_optional,
            display_order=ingredient.display_order if ingredient.display_order else idx
        )
        db.add(recipe_ingredient)
        ingredient_models.append(recipe_ingredient)

    db.flush()

    # Refresh to load relationships
    for ing in ingredient_models:
        db.refresh(ing)

    # Calculate nutrition
    nutrition = calculate_recipe_nutrition(ingredient_models, recipe.servings)
    new_recipe.total_calories = nutrition['total_calories']
    new_recipe.total_protein = nutrition['total_protein']
    new_recipe.total_carbs = nutrition['total_carbs']
    new_recipe.total_fat = nutrition['total_fat']
    new_recipe.total_fiber = nutrition['total_fiber']
    new_recipe.calories_per_serving = nutrition['calories_per_serving']
    new_recipe.protein_per_serving = nutrition['protein_per_serving']
    new_recipe.carbs_per_serving = nutrition['carbs_per_serving']
    new_recipe.fat_per_serving = nutrition['fat_per_serving']

    # Link allergens
    if recipe.allergen_ids:
        for allergen_id in recipe.allergen_ids:
            allergen = db.query(Allergen).filter(Allergen.allergen_id == allergen_id).first()
            if allergen:
                recipe_allergen = RecipeAllergen(
                    recipe_id=new_recipe.recipe_id,
                    allergen_id=allergen_id
                )
                db.add(recipe_allergen)

    db.commit()
    db.refresh(new_recipe)

    return format_recipe_response(new_recipe, db)


@router.get("/", response_model=List[RecipeResponse])
async def list_recipes(
        # Basic filters
        user_id: Optional[str] = Query(None, description="Filter by user's custom recipes"),
        meal_type: Optional[str] = Query(None, description="Filter by meal type (breakfast, lunch, dinner, snack)"),
        cuisine_type: Optional[str] = Query(None, description="Filter by cuisine type (italian, chinese, etc.)"),
        difficulty_level: Optional[str] = Query(None, description="Filter by difficulty (easy, medium, hard)"),

        # Dietary restriction filters (for all personas)
        is_vegan: Optional[bool] = Query(None, description="Filter vegan recipes"),
        is_vegetarian: Optional[bool] = Query(None, description="Filter vegetarian recipes"),
        is_gluten_free: Optional[bool] = Query(None, description="Filter gluten-free recipes (Jennifer's need)"),
        is_dairy_free: Optional[bool] = Query(None, description="Filter dairy-free recipes (Jennifer's need)"),
        is_halal: Optional[bool] = Query(None, description="Filter halal recipes (Amir's need)"),
        is_kosher: Optional[bool] = Query(None, description="Filter kosher recipes"),
        is_low_carb: Optional[bool] = Query(None, description="Filter low-carb recipes (Jason's cutting phase)"),
        is_high_protein: Optional[bool] = Query(None, description="Filter high-protein recipes (Jason's bulk phase)"),

        # Nutritional filters (Jason's primary feature)
        max_calories: Optional[int] = Query(None, description="Maximum calories per serving"),
        min_protein: Optional[int] = Query(None, description="Minimum protein (g) per serving"),
        max_carbs: Optional[int] = Query(None, description="Maximum carbs (g) per serving"),
        max_fat: Optional[int] = Query(None, description="Maximum fat (g) per serving"),

        # Time constraints (for busy users)
        max_total_time: Optional[int] = Query(None, description="Maximum total time in minutes"),
        max_prep_time: Optional[int] = Query(None, description="Maximum prep time in minutes"),

        # Allergen exclusion (Jennifer's safety feature - CRITICAL!)
        exclude_allergens: Optional[List[int]] = Query(None, description="Allergen IDs to exclude (comma-separated)"),

        # Search & pagination
        search: Optional[str] = Query(None, description="Search in recipe name and description"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
        sort_by: Optional[str] = Query("created_at",
                                       description="Sort field (created_at, recipe_name, calories_per_serving)"),
        sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),

        db: Session = Depends(get_db)
):
    """
    List and filter recipes with comprehensive filtering options

    **User Stories:**
    - Emma: Find simple, quick recipes she can make
    - Jason: Filter for high-protein, low-carb recipes matching his macros
    - Jennifer: Exclude recipes containing peanuts and dairy (allergen safety)
    - Amir: Filter only halal-certified recipes

    **Filtering Logic:**
    - All filters are applied with AND logic
    - Allergen exclusion uses NOT IN query on recipe_allergens
    - Nutritional filters apply to per_serving values
    - Search performs case-insensitive LIKE on name and description

    **Returns:**
    - Paginated list of recipes matching all filters
    - Each recipe includes full ingredient list and allergen information
    - Empty list if no matches found
    """
    # Start with base query - eager load relationships for efficiency
    query = db.query(RecipeMaster).options(
        joinedload(RecipeMaster.ingredients).joinedload(RecipeIngredient.food_item),
        joinedload(RecipeMaster.allergens)
    )

    # Apply basic filters
    if user_id:
        query = query.filter(RecipeMaster.data_source == 'user_custom')
        # In the future, add user_id filter when we have a user-recipe relationship

    if meal_type:
        query = query.filter(RecipeMaster.meal_type == meal_type)

    if cuisine_type:
        query = query.filter(RecipeMaster.cuisine_type == cuisine_type)

    if difficulty_level:
        query = query.filter(RecipeMaster.difficulty_level == difficulty_level)

    # Apply dietary restriction filters (Boolean flags)
    if is_vegan is not None:
        query = query.filter(RecipeMaster.is_vegan == is_vegan)

    if is_vegetarian is not None:
        query = query.filter(RecipeMaster.is_vegetarian == is_vegetarian)

    if is_gluten_free is not None:
        query = query.filter(RecipeMaster.is_gluten_free == is_gluten_free)

    if is_dairy_free is not None:
        query = query.filter(RecipeMaster.is_dairy_free == is_dairy_free)

    if is_halal is not None:
        query = query.filter(RecipeMaster.is_halal == is_halal)

    if is_kosher is not None:
        query = query.filter(RecipeMaster.is_kosher == is_kosher)

    if is_low_carb is not None:
        query = query.filter(RecipeMaster.is_low_carb == is_low_carb)

    if is_high_protein is not None:
        query = query.filter(RecipeMaster.is_high_protein == is_high_protein)

    # Apply nutritional filters (per serving values)
    if max_calories is not None:
        query = query.filter(RecipeMaster.calories_per_serving <= max_calories)

    if min_protein is not None:
        query = query.filter(RecipeMaster.protein_per_serving >= min_protein)

    if max_carbs is not None:
        query = query.filter(RecipeMaster.carbs_per_serving <= max_carbs)

    if max_fat is not None:
        query = query.filter(RecipeMaster.fat_per_serving <= max_fat)

    # Apply time constraint filters
    if max_total_time is not None:
        query = query.filter(RecipeMaster.total_time_minutes <= max_total_time)

    if max_prep_time is not None:
        query = query.filter(RecipeMaster.prep_time_minutes <= max_prep_time)

    # Apply allergen exclusion (CRITICAL for Jennifer's safety!)
    if exclude_allergens and len(exclude_allergens) > 0:
        # Subquery to find recipes that contain excluded allergens
        excluded_recipe_ids = db.query(RecipeAllergen.recipe_id).filter(
            RecipeAllergen.allergen_id.in_(exclude_allergens)
        ).distinct()

        # Exclude those recipes from main query
        query = query.filter(~RecipeMaster.recipe_id.in_(excluded_recipe_ids))

    # Apply full-text search on name and description
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (RecipeMaster.recipe_name.ilike(search_pattern)) |
            (RecipeMaster.description.ilike(search_pattern))
        )

    # Apply sorting
    valid_sort_fields = {
        'created_at': RecipeMaster.created_at,
        'recipe_name': RecipeMaster.recipe_name,
        'calories_per_serving': RecipeMaster.calories_per_serving,
        'total_time_minutes': RecipeMaster.total_time_minutes,
        'prep_time_minutes': RecipeMaster.prep_time_minutes
    }

    if sort_by in valid_sort_fields:
        sort_field = valid_sort_fields[sort_by]
        if sort_order == 'asc':
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
    else:
        # Default sort: newest first
        query = query.order_by(RecipeMaster.created_at.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    recipes = query.offset(offset).limit(page_size).all()

    # Format responses
    result = []
    for recipe in recipes:
        result.append(format_recipe_response(recipe, db))

    return result


@router.get("/recommend", response_model=List[RecipeMatchScore])
async def recommend_recipes_from_inventory(
        user_id: str = Query(..., description="User ID"),

        # Optional filters to narrow recommendations
        meal_type: Optional[str] = Query(None, description="Filter by meal type"),
        is_vegan: Optional[bool] = Query(None, description="Filter vegan recipes"),
        is_vegetarian: Optional[bool] = Query(None, description="Filter vegetarian recipes"),
        is_halal: Optional[bool] = Query(None, description="Filter halal recipes"),
        is_gluten_free: Optional[bool] = Query(None, description="Filter gluten-free recipes"),

        # Recommendation parameters
        min_match_score: float = Query(40.0, ge=0, le=100, description="Minimum match percentage"),
        limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),

        db: Session = Depends(get_db)
):
    """
    Smart Recipe Recommendations
    - Filters by User Dietary Profile (Automatic)
    - Filters by Request Parameters (Manual Override)
    - Scores based on Inventory Availability
    """
    # 1. FETCH USER PROFILE (Personalization)
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    user = db.query(User).filter(User.user_id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. GET USER INVENTORY (Non-expired items)
    from datetime import date

    user_inventory = db.query(UserInventory).filter(
        UserInventory.user_id == user_uuid,
        UserInventory.expiry_date >= date.today()
    ).options(
        joinedload(UserInventory.food_item)
    ).all()


    if not user_inventory:
        return []

    # Create lookup sets
    available_food_ids = set([str(item.food_id) for item in user_inventory])

    # Track expiring items (next 3 days) for bonus points
    expiring_soon_ids = set([
        str(item.food_id) for item in user_inventory
        if item.expiry_date <= date.today() + timedelta(days=3)
    ])

    # 3. BUILD RECIPE QUERY
    query = db.query(RecipeMaster).options(
        joinedload(RecipeMaster.ingredients).joinedload(RecipeIngredient.food_item),
        joinedload(RecipeMaster.allergens)
    )

    total_recipes = query.count()

    # --- APPLY AUTOMATIC USER PREFERENCES ---
    # These act as "hard filters" - if you are Vegan, you ONLY see Vegan.
    if user.is_vegan:
        query = query.filter(RecipeMaster.is_vegan == True)
    if user.is_vegetarian:
        query = query.filter(RecipeMaster.is_vegetarian == True)
    if user.is_gluten_free:
        query = query.filter(RecipeMaster.is_gluten_free == True)
    if user.is_dairy_free:
        query = query.filter(RecipeMaster.is_dairy_free == True)
    if user.is_halal:
        query = query.filter(RecipeMaster.is_halal == True)
    if user.is_kosher:
        query = query.filter(RecipeMaster.is_kosher == True)

    # --- APPLY MANUAL FILTERS ---
    # These allow refining the results further (e.g., "I want a Vegan Dinner")
    if meal_type:
        query = query.filter(RecipeMaster.meal_type == meal_type)

    # If manual toggles are passed (overriding or adding to profile), apply them
    if is_vegan is not None:
        query = query.filter(RecipeMaster.is_vegan == is_vegan)
    if is_vegetarian is not None:
        query = query.filter(RecipeMaster.is_vegetarian == is_vegetarian)
    if is_halal is not None:
        query = query.filter(RecipeMaster.is_halal == is_halal)
    if is_gluten_free is not None:
        query = query.filter(RecipeMaster.is_gluten_free == is_gluten_free)

    recipes = query.all()

    # 4. SCORING ALGORITHM
    recommendations = []


    for recipe in recipes:
        if not recipe.ingredients:
            continue

        total_ingredients = len(recipe.ingredients)

        # Count non-optional ingredients
        required_ingredients = [ing for ing in recipe.ingredients if not ing.is_optional]

        available_count = 0
        required_available = 0
        expiring_ingredient_count = 0
        missing_ingredients = []

        for ing in recipe.ingredients:
            ing_food_id = str(ing.food_id)

            if ing_food_id in available_food_ids:
                available_count += 1
                if not ing.is_optional:
                    required_available += 1

                # Bonus: Uses expiring item
                if ing_food_id in expiring_soon_ids:
                    expiring_ingredient_count += 1
            else:
                missing_ingredients.append(ing.food_item.name)

        match_count = 0
        for ing in recipe.ingredients:
            ing_id = str(ing.food_id)
            has_item = ing_id in available_food_ids
            if has_item: match_count += 1

        # Calculate Base Score (0-100)
        base_match_score = (available_count / total_ingredients) * 100

        # Bonus: +10% max for using expiring food
        expiring_bonus = min((expiring_ingredient_count / total_ingredients) * 10, 10)

        final_score = base_match_score + expiring_bonus


        if final_score < min_match_score:
            continue

        # Filter by minimum score
        if final_score < min_match_score:
            continue

        # Track required missing count
        required_missing = len(required_ingredients) - required_available

        recommendations.append({
            'recipe': format_recipe_response(recipe, db),
            'match_score': round(final_score, 2),
            'available_ingredients': available_count,
            'total_ingredients': total_ingredients,
            'missing_ingredients': missing_ingredients,
            # Helper fields for sorting
            'required_missing': required_missing,
            'uses_expiring': expiring_ingredient_count > 0
        })

    # 5. SORTING
    # Priority:
    # 1. Can make it NOW (0 missing required ingredients)
    # 2. Saves food (Uses expiring items)
    # 3. High match score
    recommendations.sort(
        key=lambda x: (
            x['required_missing'] == 0,  # True (1) comes before False (0)
            x['uses_expiring'],
            x['match_score']
        ),
        reverse=True
    )

    return recommendations[:limit]


@router.get("/search/external")
async def search_external_recipes(
        query: str = Query(..., description="Search query"),
        dietary_restrictions: Optional[List[str]] = Query(None),
        cuisine_type: Optional[str] = Query(None),
        meal_type: Optional[str] = Query(None),
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """
    Search recipes from Edamam API.
    Returns raw Edamam results formatted for preview.
    """
    results = await edamam_service.search_recipes(
        query=query,
        health=dietary_restrictions,
        cuisine_type=cuisine_type,
        meal_type=meal_type
    )

    if not results or "hits" not in results:
        return []

    formatted_results = []
    for hit in results["hits"]:
        recipe = hit["recipe"]
        formatted_results.append({
            "recipe_name": recipe["label"],
            "image_url": recipe["image"],
            "source_url": recipe["url"],
            "calories": round(recipe["calories"]),
            "servings": recipe["yield"],
            "ingredients_count": len(recipe["ingredients"]),
            "diet_labels": recipe["dietLabels"] + recipe["healthLabels"],
            # Send the URI so the frontend can call /import with it
            "import_uri": recipe["uri"]
        })

    return formatted_results[:limit]


# ============================================
# USER RECIPE MANAGEMENT
# ============================================

@router.post("/{recipe_id}/save", status_code=201)
async def save_recipe(
        recipe_id: str,
        request: SaveRecipeRequest,
        user_id: str = Query(..., description="User ID saving the recipe"),
        db: Session = Depends(get_db)
):
    """
    Save/favorite a recipe to user's collection

    **Features:**
    - Idempotent: Can call multiple times without error
    - Optional user notes
    - Timestamp tracking (saved_at)

    **Use Cases:**
    - User finds recipe they want to try later
    - User marks favorites for easy access
    - User adds notes about modifications they made

    **Returns:**
    - Success message
    - Saved recipe details
    """
    # TODO: Implementation
    # 1. Verify recipe exists
    # 2. Check if already saved (user_id, recipe_id in user_saved_recipes)
    # 3. If already saved, update notes if provided
    # 4. If not saved, create entry in user_saved_recipes
    # 5. Return success response
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
        recipe_id: str,
        db: Session = Depends(get_db)
):
    """
    Get detailed recipe information
    """
    # 1. Query recipe by UUID
    # We use options(joinedload(...)) to efficiently fetch related data in one query
    recipe = db.query(RecipeMaster).filter(
        RecipeMaster.recipe_id == UUID(recipe_id)
    ).options(
        joinedload(RecipeMaster.ingredients).joinedload(RecipeIngredient.food_item),
        joinedload(RecipeMaster.allergens)
    ).first()

    # 2. Return 404 if not found
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # 3. Return formatted response
    return format_recipe_response(recipe, db)


@router.put("/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(
        recipe_id: str,
        updates: RecipeUpdate,
        user_id: str = Query(..., description="User ID updating the recipe"),
        db: Session = Depends(get_db)
):
    """
    Update a custom recipe

    **Authorization:**
    - Only the user who created the recipe can update it
    - Edamam-imported recipes (data_source='edamam') cannot be modified

    **Partial Updates:**
    - Only fields provided in request will be updated
    - Ingredients list can be replaced entirely
    - Allergens will be recalculated if ingredients change

    **Errors:**
    - 404: Recipe not found
    - 403: User doesn't own recipe or recipe is from Edamam
    """
    # TODO: Implementation
    # 1. Query existing recipe
    # 2. Verify user owns recipe (check data_source='user_custom')
    # 3. Update only provided fields
    # 4. If ingredients updated, delete old and create new recipe_ingredients
    # 5. Recalculate nutritional values if servings or ingredients changed
    # 6. Update updated_at timestamp
    # 7. Return updated RecipeResponse
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
        recipe_id: str,
        user_id: str = Query(..., description="User ID deleting the recipe"),
        db: Session = Depends(get_db)
):
    """
    Delete a custom recipe

    **Authorization:**
    - Only the user who created the recipe can delete it
    - Edamam-imported recipes cannot be deleted (only unsaved)

    **Cascade:**
    - Automatically deletes associated recipe_ingredients
    - Automatically deletes associated recipe_allergens
    - Removes from user_saved_recipes for all users

    **Errors:**
    - 404: Recipe not found
    - 403: User doesn't own recipe or recipe is from Edamam
    """
    # TODO: Implementation
    # 1. Query existing recipe
    # 2. Verify user owns recipe (data_source='user_custom')
    # 3. Delete recipe (cascades to ingredients and allergens)
    # 4. Return 204 No Content
    raise HTTPException(status_code=501, detail="Not implemented yet")


# ============================================
# SMART RECOMMENDATIONS
# ============================================




# ============================================
# EDAMAM INTEGRATION
# ============================================

@router.post("/import/edamam", response_model=RecipeResponse)
async def import_from_edamam(
        edamam_uri: str = Query(..., description="Edamam recipe URI (or ID)"),
        user_id: str = Query(..., description="User ID importing the recipe"),
        db: Session = Depends(get_db)
):
    """
    Import a recipe from Edamam API into local database.
    Maps ingredients to FoodItemMaster and saves the recipe.
    """
    # 1. Check if already imported
    existing = db.query(RecipeMaster).filter(RecipeMaster.edamam_recipe_uri == edamam_uri).first()
    if existing:
        return format_recipe_response(existing, db)

    # 2. Fetch details from API
    data = await edamam_service.get_recipe_by_uri(edamam_uri)
    if not data or "recipe" not in data:
        raise HTTPException(status_code=404, detail="Recipe not found on Edamam")

    recipe_data = data["recipe"]

    # 3. Create Recipe Master Record
    new_recipe = RecipeMaster(
        edamam_recipe_uri=edamam_uri,
        recipe_name=recipe_data["label"],
        image_url=recipe_data["image"],
        source_url=recipe_data["url"],
        servings=int(recipe_data["yield"]),
        total_time_minutes=int(recipe_data["totalTime"]),
        total_calories=Decimal(recipe_data["calories"]),
        cuisine_type=recipe_data["cuisineType"][0] if recipe_data.get("cuisineType") else "Global",
        meal_type=recipe_data["mealType"][0] if recipe_data.get("mealType") else None,
        data_source='edamam',

        is_vegan="Vegan" in recipe_data["healthLabels"],
        is_vegetarian="Vegetarian" in recipe_data["healthLabels"],
        is_gluten_free="Gluten-Free" in recipe_data["healthLabels"],
        is_dairy_free="Dairy-Free" in recipe_data["healthLabels"],
        is_halal="Halal" in recipe_data["healthLabels"],
        is_kosher="Kosher" in recipe_data["healthLabels"]
    )

    db.add(new_recipe)
    db.flush()

    # 4. Process Ingredients
    for ing in recipe_data["ingredients"]:
        food_id = ing.get("foodId")
        food_item = None

        if food_id:
            food_item = db.query(FoodItemMaster).filter(FoodItemMaster.edamam_food_id == food_id).first()

        if not food_item:
            food_item = FoodItemMaster(
                name=ing["food"],
                category=ing.get("foodCategory"),
                image_url=ing.get("image"),
                edamam_food_id=food_id,
                data_source="edamam"
            )
            db.add(food_item)
            db.flush()

        # --- FIX START: Sanitize Unit ---
        raw_unit = ing.get("measure")
        clean_unit = raw_unit

        # Edamam returns "<unit>" or null for whole items (e.g. 1 apple)
        if not raw_unit or raw_unit == "<unit>":
            clean_unit = "count"
            # --- FIX END ---

        recipe_ing = RecipeIngredient(
            recipe_id=new_recipe.recipe_id,
            food_id=food_item.food_id,
            quantity=ing["quantity"] if ing["quantity"] else 1,
            unit=clean_unit,  # <--- Use the sanitized unit
            ingredient_note=ing["text"],
            is_optional=False
        )
        db.add(recipe_ing)

    db.commit()
    db.refresh(new_recipe)

    return format_recipe_response(new_recipe, db)





@router.delete("/{recipe_id}/save", status_code=204)
async def unsave_recipe(
        recipe_id: str,
        user_id: str = Query(..., description="User ID unsaving the recipe"),
        db: Session = Depends(get_db)
):
    """
    Remove recipe from user's saved collection

    **Features:**
    - Idempotent: Can call even if not saved
    - Only removes from user's collection (doesn't delete recipe)

    **Note:**
    - This is different from DELETE /recipes/{id}
    - DELETE /recipes/{id} deletes custom recipes permanently
    - This just removes from user's favorites
    """
    # TODO: Implementation
    # 1. Delete from user_saved_recipes where user_id and recipe_id match
    # 2. Return 204 No Content (even if wasn't saved)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/saved", response_model=List[RecipeResponse])
async def get_saved_recipes(
        user_id: str = Query(..., description="User ID"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db)
):
    """
    Get user's saved/favorite recipes

    **Returns:**
    - Paginated list of saved recipes
    - Includes user's personal notes if any
    - Sorted by saved_at DESC (most recently saved first)

    **Use Cases:**
    - User wants to see their recipe collection
    - User looks for that recipe they saved last week
    - User reviews their favorite recipes
    """
    # TODO: Implementation
    # 1. Query user_saved_recipes with user_id
    # 2. JOIN recipes_master
    # 3. Eager load ingredients and allergens
    # 4. Order by saved_at DESC
    # 5. Apply pagination
    # 6. Return List[RecipeResponse] with notes
    raise HTTPException(status_code=501, detail="Not implemented yet")


# ============================================
# STATISTICS & ANALYTICS (Future Enhancement)
# ============================================

@router.get("/stats/popular", response_model=List[RecipeResponse])
async def get_popular_recipes(
        limit: int = Query(10, ge=1, le=50),
        db: Session = Depends(get_db)
):
    """
    Get most popular recipes (most saved by users)

    **Future Enhancement**
    """
    # TODO: Implementation
    # 1. Query recipes with COUNT of user_saved_recipes
    # 2. Order by save count DESC
    # 3. Limit to top N
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/stats/trending", response_model=List[RecipeResponse])
async def get_trending_recipes(
        days: int = Query(7, ge=1, le=30),
        limit: int = Query(10, ge=1, le=50),
        db: Session = Depends(get_db)
):
    """
    Get trending recipes (most saves in recent days)

    **Future Enhancement**
    """
    # TODO: Implementation
    # 1. Query user_saved_recipes where saved_at > (now - days)
    # 2. Group by recipe_id, COUNT saves
    # 3. Order by count DESC
    # 4. Limit to top N
    raise HTTPException(status_code=501, detail="Not implemented yet")