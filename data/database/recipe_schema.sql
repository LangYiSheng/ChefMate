CREATE DATABASE IF NOT EXISTS chefmate_data
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE chefmate_data;

SET NAMES utf8mb4;

DROP TABLE IF EXISTS recipe_tag_map;
DROP TABLE IF EXISTS recipe_tag;
DROP TABLE IF EXISTS recipe_tag_category;
DROP TABLE IF EXISTS recipe_step;
DROP TABLE IF EXISTS recipe_ingredient;
DROP TABLE IF EXISTS recipe;

CREATE TABLE recipe (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '菜谱主键',
    name VARCHAR(128) NOT NULL COMMENT '菜品名',
    aliases_json JSON NULL COMMENT '菜品别名列表',
    description TEXT NULL COMMENT '菜品描述',
    difficulty ENUM('简单', '中等', '困难') NOT NULL DEFAULT '简单' COMMENT '难度',
    estimated_minutes INT NOT NULL DEFAULT 15 COMMENT '预计制作时长（分钟）',
    servings INT NOT NULL DEFAULT 2 COMMENT '默认份量',
    tips TEXT NULL COMMENT '补充提示',
    status ENUM('DRAFT', 'PUBLISHED') NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_recipe_name (name),
    KEY idx_recipe_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜谱基础信息表';

CREATE TABLE recipe_ingredient (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    recipe_id BIGINT UNSIGNED NOT NULL COMMENT '菜谱 ID',
    ingredient_name VARCHAR(64) NOT NULL COMMENT '食材名',
    amount_value DECIMAL(10,2) NULL COMMENT '数量值，可为空',
    amount_text VARCHAR(64) NOT NULL COMMENT '数量描述，如2个、少许、适量',
    unit VARCHAR(32) NULL COMMENT '单位',
    is_optional TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否可选',
    purpose VARCHAR(255) NULL COMMENT '用途说明',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    CONSTRAINT fk_recipe_ingredient_recipe
        FOREIGN KEY (recipe_id) REFERENCES recipe(id)
        ON DELETE CASCADE,
    KEY idx_recipe_ingredient_recipe (recipe_id),
    KEY idx_recipe_ingredient_name (ingredient_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜谱食材表';

CREATE TABLE recipe_step (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    recipe_id BIGINT UNSIGNED NOT NULL COMMENT '菜谱 ID',
    step_no INT NOT NULL COMMENT '步骤序号',
    title VARCHAR(128) NULL COMMENT '步骤标题',
    instruction TEXT NOT NULL COMMENT '步骤内容',
    timer_seconds INT NULL COMMENT '建议计时秒数',
    notes VARCHAR(255) NULL COMMENT '补充提醒',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    CONSTRAINT fk_recipe_step_recipe
        FOREIGN KEY (recipe_id) REFERENCES recipe(id)
        ON DELETE CASCADE,
    UNIQUE KEY uk_recipe_step_no (recipe_id, step_no),
    KEY idx_recipe_step_recipe (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜谱步骤表';

CREATE TABLE recipe_tag_category (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    category_code VARCHAR(32) NOT NULL COMMENT '分类编码',
    category_name VARCHAR(64) NOT NULL COMMENT '分类名称',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    PRIMARY KEY (id),
    UNIQUE KEY uk_recipe_tag_category_code (category_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜谱标签分类表';

CREATE TABLE recipe_tag (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    category_id BIGINT UNSIGNED NOT NULL COMMENT '分类 ID',
    bit_position INT NOT NULL COMMENT '固定 bit 位',
    tag_code VARCHAR(64) NOT NULL COMMENT '标签编码',
    tag_name VARCHAR(64) NOT NULL COMMENT '标签名',
    is_enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    PRIMARY KEY (id),
    CONSTRAINT fk_recipe_tag_category
        FOREIGN KEY (category_id) REFERENCES recipe_tag_category(id)
        ON DELETE CASCADE,
    UNIQUE KEY uk_recipe_tag_code (tag_code),
    UNIQUE KEY uk_recipe_tag_bit (category_id, bit_position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='固定标签字典表';

CREATE TABLE recipe_tag_map (
    recipe_id BIGINT UNSIGNED NOT NULL COMMENT '菜谱 ID',
    tag_id BIGINT UNSIGNED NOT NULL COMMENT '标签 ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (recipe_id, tag_id),
    CONSTRAINT fk_recipe_tag_map_recipe
        FOREIGN KEY (recipe_id) REFERENCES recipe(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_recipe_tag_map_tag
        FOREIGN KEY (tag_id) REFERENCES recipe_tag(id)
        ON DELETE CASCADE,
    KEY idx_recipe_tag_map_tag (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜谱与标签关联表';

INSERT INTO recipe_tag_category (category_code, category_name, sort_order) VALUES
('flavor', '口味标签', 1),
('method', '烹饪方式标签', 2),
('scene', '场景标签', 3),
('health', '健康标签', 4),
('difficulty', '难度标签', 5),
('time', '时间标签', 6),
('tool', '厨具标签', 7);

INSERT INTO recipe_tag (category_id, bit_position, tag_code, tag_name, sort_order)
SELECT c.id, t.bit_position, t.tag_code, t.tag_name, t.sort_order
FROM recipe_tag_category c
JOIN (
    SELECT 'flavor' AS category_code, 0 AS bit_position, 'flavor_light' AS tag_code, '清淡' AS tag_name, 1 AS sort_order
    UNION ALL SELECT 'flavor', 1, 'flavor_savory', '咸鲜', 2
    UNION ALL SELECT 'flavor', 2, 'flavor_sweet_sour', '酸甜', 3
    UNION ALL SELECT 'flavor', 3, 'flavor_hot_sour', '酸辣', 4
    UNION ALL SELECT 'flavor', 4, 'flavor_spicy', '香辣', 5
    UNION ALL SELECT 'flavor', 5, 'flavor_mala', '麻辣', 6
    UNION ALL SELECT 'flavor', 6, 'flavor_garlic', '蒜香', 7
    UNION ALL SELECT 'flavor', 7, 'flavor_curry', '咖喱', 8

    UNION ALL SELECT 'method', 0, 'method_stir_fry', '炒', 1
    UNION ALL SELECT 'method', 1, 'method_pan_fry', '煎', 2
    UNION ALL SELECT 'method', 2, 'method_steam', '蒸', 3
    UNION ALL SELECT 'method', 3, 'method_boil', '煮', 4
    UNION ALL SELECT 'method', 4, 'method_stew', '炖', 5
    UNION ALL SELECT 'method', 5, 'method_braise', '焖', 6
    UNION ALL SELECT 'method', 6, 'method_cold_mix', '凉拌', 7
    UNION ALL SELECT 'method', 7, 'method_bake', '烤', 8
    UNION ALL SELECT 'method', 8, 'method_deep_fry', '炸', 9

    UNION ALL SELECT 'scene', 0, 'scene_quick', '快手', 1
    UNION ALL SELECT 'scene', 1, 'scene_home_style', '家常', 2
    UNION ALL SELECT 'scene', 2, 'scene_single_meal', '一人食', 3
    UNION ALL SELECT 'scene', 3, 'scene_with_rice', '下饭', 4
    UNION ALL SELECT 'scene', 4, 'scene_dorm', '宿舍友好', 5

    UNION ALL SELECT 'health', 0, 'health_low_oil', '低油', 1
    UNION ALL SELECT 'health', 1, 'health_high_protein', '高蛋白', 2
    UNION ALL SELECT 'health', 2, 'health_fat_loss', '减脂友好', 3
    UNION ALL SELECT 'health', 3, 'health_light_diet', '清淡饮食', 4
    UNION ALL SELECT 'health', 4, 'health_vegetarian_friendly', '素食友好', 5

    UNION ALL SELECT 'difficulty', 0, 'difficulty_easy', '简单', 1
    UNION ALL SELECT 'difficulty', 1, 'difficulty_medium', '中等', 2
    UNION ALL SELECT 'difficulty', 2, 'difficulty_hard', '困难', 3

    UNION ALL SELECT 'time', 0, 'time_10m', '10分钟内', 1
    UNION ALL SELECT 'time', 1, 'time_10_20m', '10到20分钟', 2
    UNION ALL SELECT 'time', 2, 'time_20_30m', '20到30分钟', 3
    UNION ALL SELECT 'time', 3, 'time_30_60m', '30到60分钟', 4
    UNION ALL SELECT 'time', 4, 'time_60m_plus', '60分钟以上', 5

    UNION ALL SELECT 'tool', 0, 'tool_wok', '炒锅', 1
    UNION ALL SELECT 'tool', 1, 'tool_pot', '汤锅', 2
    UNION ALL SELECT 'tool', 2, 'tool_steamer', '蒸锅', 3
    UNION ALL SELECT 'tool', 3, 'tool_rice_cooker', '电饭煲', 4
    UNION ALL SELECT 'tool', 4, 'tool_air_fryer', '空气炸锅', 5
    UNION ALL SELECT 'tool', 5, 'tool_oven', '烤箱', 6
    UNION ALL SELECT 'tool', 6, 'tool_microwave', '微波炉', 7
) t ON t.category_code = c.category_code;
