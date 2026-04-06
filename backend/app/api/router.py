from fastapi import APIRouter

from app.api.routes import auth, conversations, files, profiles, recipes, voice

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profiles.router, prefix="/profile", tags=["profile"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
