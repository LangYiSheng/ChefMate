from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    user_id: str
    flavor_preferences: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    health_goal: str | None = None
    cooking_skill_level: str | None = None
    max_cook_time: int | None = None
    available_tools: list[str] = Field(default_factory=list)


class ProfileUpdateRequest(BaseModel):
    flavor_preferences: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    health_goal: str | None = None
    cooking_skill_level: str | None = None
    max_cook_time: int | None = None
    available_tools: list[str] = Field(default_factory=list)
