from fastapi import APIRouter, Query

from app.skills.recommendation import recommendation_skill

router = APIRouter()


@router.get("/by-name")
def search_recipes_by_name(
    query: str,
    exact: bool = False,
    limit: int = Query(default=10, ge=1, le=50),
):
    return recommendation_skill.search_recipes_by_name(query=query, exact=exact, limit=limit)


@router.get("/by-tags")
def filter_recipes_by_tags(
    flavor: list[str] = Query(default_factory=list),
    method: list[str] = Query(default_factory=list),
    scene: list[str] = Query(default_factory=list),
    health: list[str] = Query(default_factory=list),
    time: list[str] = Query(default_factory=list),
    tool: list[str] = Query(default_factory=list),
    difficulty: list[str] = Query(default_factory=list),
    match_mode: str = Query(default="fuzzy", pattern="^(exact|fuzzy)$"),
    limit: int = Query(default=10, ge=1, le=50),
):
    return recommendation_skill.filter_recipes_by_tags(
        flavor=flavor,
        method=method,
        scene=scene,
        health=health,
        time=time,
        tool=tool,
        difficulty=difficulty,
        match_mode=match_mode,
        limit=limit,
    )


@router.get("/by-ingredients")
def find_recipes_by_ingredients(
    ingredients: list[str] = Query(default_factory=list),
    exact_only: bool = False,
    limit: int = Query(default=10, ge=1, le=50),
):
    return recommendation_skill.find_recipes_by_ingredients(
        ingredients=ingredients,
        exact_only=exact_only,
        limit=limit,
    )


@router.get("/recipes/{recipe_id}")
def get_recipe_by_id(
    recipe_id: int,
    include: list[str] = Query(default=["recipe", "tags", "ingredients", "steps"]),
):
    return recommendation_skill.get_recipe_by_id(recipe_id, include=include)
