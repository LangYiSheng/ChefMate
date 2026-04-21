from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import TagSelections


class UserMemoryUpdateInput(BaseModel):
    cooking_preference_text: str | None = None
    tag_selections: TagSelections | None = None
    complete_workspace_onboarding: bool | None = None


class RecommendRecipesInput(BaseModel):
    keyword: str | None = Field(
        default=None,
        description="开放推荐时的关键词。用户点名一道具体菜时不要用本工具，改用 search_recipes。",
    )
    ingredients: list[str] = Field(default_factory=list, description="用户明确拥有或想使用的食材。")
    flavor: list[str] = Field(default_factory=list, description="口味标签，必须来自可用标签目录。")
    method: list[str] = Field(default_factory=list, description="做法标签，必须来自可用标签目录。")
    scene: list[str] = Field(default_factory=list, description="场景标签，必须来自可用标签目录。")
    health: list[str] = Field(default_factory=list, description="健康标签，必须来自可用标签目录。")
    time: list[str] = Field(default_factory=list, description="时间标签，必须来自可用标签目录。")
    tool: list[str] = Field(default_factory=list, description="厨具标签，必须来自可用标签目录。")
    difficulty: list[str] = Field(default_factory=list, description="难度，只能是简单、中等、困难。")


class RecipeSearchInput(BaseModel):
    query: str | None = Field(
        default=None,
        description="用户说出的完整菜名或搜索词，保留原文，例如“西红柿炒鸡蛋”。",
    )
    ingredients: list[str] = Field(
        default_factory=list,
        description="从菜名或用户描述中明确拆出的食材，例如“西红柿炒鸡蛋”拆成西红柿、鸡蛋。",
    )
    step_text: str | None = Field(
        default=None,
        description="按步骤/做法文本搜索时使用，例如“空气炸锅180度烤”；具体菜名不要填这个字段。",
    )
    flavor: list[str] = Field(default_factory=list, description="可选口味标签，必须来自可用标签目录。")
    method: list[str] = Field(default_factory=list, description="可选做法标签，必须来自可用标签目录。")
    scene: list[str] = Field(default_factory=list, description="可选场景标签，必须来自可用标签目录。")
    health: list[str] = Field(default_factory=list, description="可选健康标签，必须来自可用标签目录。")
    time: list[str] = Field(default_factory=list, description="可选时间标签，必须来自可用标签目录。")
    tool: list[str] = Field(default_factory=list, description="可选厨具标签，必须来自可用标签目录。")
    difficulty: list[str] = Field(default_factory=list, description="可选难度，只能是简单、中等、困难。")
    name_match_first: bool = Field(
        default=True,
        description="保持为 true：先按完整菜名查数据库；没有合适结果时再按食材和标签/步骤文本查。",
    )
    limit: int = Field(default=3, ge=1, le=6, description="最多返回的数据库候选数量。")


class GeneratedRecipeIngredientInput(BaseModel):
    id: str | None = Field(default=None, description="可省略；系统会自动补齐稳定内部 id。")
    ingredient_name: str = Field(description="食材名称，例如“鸡蛋”。")
    amount_text: str = Field(default="适量", description="展示给用户看的用量，例如“2 个”或“少许”。")
    amount_value: float | None = None
    unit: str | None = None
    is_optional: bool = False
    purpose: str | None = None
    sort_order: int | None = Field(default=None, description="可省略；系统会按列表顺序补齐。")


class GeneratedRecipeStepInput(BaseModel):
    id: str | None = Field(default=None, description="可省略；系统会自动补齐稳定内部 id。")
    step_no: int = Field(description="步骤序号，从 1 开始连续递增。")
    title: str | None = None
    instruction: str = Field(description="具体操作说明。")
    timer_seconds: int | None = None
    notes: str | None = None


class GeneratedRecipeInput(BaseModel):
    name: str = Field(description="现写菜谱名称。")
    description: str = ""
    difficulty: str = "简单"
    estimated_minutes: int = 15
    servings: int = 2
    tags: dict[str, list[str]] = Field(default_factory=dict, description="可选标签，类别建议使用 flavor/method/scene/health/time/tool。")
    ingredients: list[GeneratedRecipeIngredientInput] = Field(default_factory=list, description="至少 1 项食材。")
    steps: list[GeneratedRecipeStepInput] = Field(default_factory=list, description="至少 1 个步骤。")
    tips: str | None = None


class TaskRecipeUpsertInput(BaseModel):
    recipe_id: int | None = Field(
        default=None,
        description="数据库菜谱 id。复制数据库菜谱时只传这个字段，不要同时传 recipe。",
    )
    recipe: GeneratedRecipeInput | None = Field(
        default=None,
        description="用户明确同意现写后才传完整新菜谱；不要作为数据库搜索失败时的自动兜底。",
    )


class IngredientPatchInput(BaseModel):
    id: str | None = Field(default=None, description="优先使用当前菜谱快照里的食材 id 定位。")
    ingredient_name: str | None = Field(default=None, description="没有 id 时用食材名定位，例如“鸡蛋”。")
    amount_text: str | None = Field(default=None, description="展示用量，例如“2 个”。")
    amount_value: float | None = None
    unit: str | None = None
    is_optional: bool | None = None
    purpose: str | None = None
    sort_order: int | None = None
    status: str | None = Field(default=None, description="食材准备状态，只能是 pending、ready、skipped。")
    note: str | None = Field(default=None, description="关于这个食材的临时备注。")


class StepPatchInput(BaseModel):
    id: str | None = Field(default=None, description="优先使用当前菜谱快照里的步骤 id 定位。")
    step_no: int | None = Field(default=None, description="没有 id 时用步骤序号定位。")
    title: str | None = None
    instruction: str | None = None
    timer_seconds: int | None = None
    notes: str | None = None
    status: str | None = Field(default=None, description="步骤状态，只能是 pending、current、done。")
    note: str | None = Field(default=None, description="关于这个步骤的临时备注。")


class TaskRecipePatchInput(BaseModel):
    ingredients: list[IngredientPatchInput] = Field(
        default_factory=list,
        description="备料阶段更新食材状态/备注；烹饪阶段不要传 ingredients。",
    )
    steps: list[StepPatchInput] = Field(
        default_factory=list,
        description="烹饪阶段更新步骤状态/备注；备料阶段仅在确实需要微调步骤说明时传。",
    )


class PlanningRecipePatchInput(TaskRecipePatchInput):
    name: str | None = Field(default=None, description="推荐阶段可局部修改当前任务菜谱名称。")
    description: str | None = Field(default=None, description="推荐阶段可局部修改菜谱简介。")
    difficulty: str | None = Field(default=None, description="推荐阶段可局部修改难度。")
    estimated_minutes: int | None = Field(default=None, ge=1, description="推荐阶段可局部修改预计耗时。")
    servings: int | None = Field(default=None, ge=1, description="推荐阶段可局部修改份量。")
    tags: dict[str, list[str]] | None = Field(default=None, description="推荐阶段可局部修改标签。")
    tips: str | None = Field(default=None, description="推荐阶段可局部修改小贴士。")


class RecipeDetailDisplayInput(BaseModel):
    recipe_id: int | None = None


class ImageRecognitionInput(BaseModel):
    image_url: str
    user_hint: str | None = None
