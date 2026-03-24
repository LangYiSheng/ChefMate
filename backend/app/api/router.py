from fastapi import APIRouter

from app.api.routes import conversations, profiles, recipes, recommendations, tasks, vision

api_router = APIRouter()
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(profiles.router, prefix="/users/profile", tags=["profile"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
