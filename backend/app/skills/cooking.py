class CookingSkill:
    name = "cooking"

    def guide_placeholder(self) -> dict:
        return {
            "recipe_name": "西红柿炒鸡蛋",
            "steps": [
                {"step_no": 1, "instruction": "西红柿切块，鸡蛋打散。", "timer_seconds": None},
                {"step_no": 2, "instruction": "炒鸡蛋后盛出。", "timer_seconds": 120},
                {"step_no": 3, "instruction": "炒番茄出汁，再回锅鸡蛋。", "timer_seconds": 180},
            ],
        }


cooking_skill = CookingSkill()
