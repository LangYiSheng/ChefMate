class PreparationSkill:
    name = "preparation"

    def check_placeholder(self) -> dict:
        return {
            "required": [
                {"ingredient_name": "西红柿", "amount_text": "2个"},
                {"ingredient_name": "鸡蛋", "amount_text": "3个"},
            ],
            "missing": [],
            "status": "READY",
        }


preparation_skill = PreparationSkill()
