from fastapi import APIRouter

from app.api.routes import conversations, profiles, recipes, recommendations, tasks

api_router = APIRouter()
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(profiles.router, prefix="/users/profile", tags=["profile"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
