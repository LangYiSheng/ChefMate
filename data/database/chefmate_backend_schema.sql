USE chefmate;

SET NAMES utf8mb4;

DROP TABLE IF EXISTS conversation_message_attachment;
DROP TABLE IF EXISTS conversation_message;
DROP TABLE IF EXISTS conversation_task;
DROP TABLE IF EXISTS conversation;
DROP TABLE IF EXISTS uploaded_asset;
DROP TABLE IF EXISTS auth_session;
DROP TABLE IF EXISTS user_preference_tag;
DROP TABLE IF EXISTS chefmate_user;

CREATE TABLE chefmate_user (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户主键',
    username VARCHAR(32) NOT NULL COMMENT '用户名',
    email VARCHAR(191) NULL COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    display_name VARCHAR(64) NOT NULL COMMENT '展示名称',
    allow_auto_update TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否允许自动更新偏好',
    auto_start_step_timer TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否自动开启步骤计时',
    cooking_preference_text TEXT NOT NULL COMMENT '用户偏好文本',
    is_first_workspace_visit TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否首次进入工作台',
    has_completed_workspace_onboarding TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否完成首次引导',
    profile_completed_at DATETIME NULL COMMENT '完成档案初始化时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_chefmate_user_username (username),
    UNIQUE KEY uk_chefmate_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ChefMate 用户表';

CREATE TABLE user_preference_tag (
    user_id BIGINT UNSIGNED NOT NULL COMMENT '用户 ID',
    tag_id BIGINT UNSIGNED NOT NULL COMMENT '标签 ID，直接引用 recipe_tag',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (user_id, tag_id),
    CONSTRAINT fk_user_preference_tag_user
        FOREIGN KEY (user_id) REFERENCES chefmate_user(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_preference_tag_tag
        FOREIGN KEY (tag_id) REFERENCES recipe_tag(id)
        ON DELETE CASCADE,
    KEY idx_user_preference_tag_tag (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户长期偏好标签表';

CREATE TABLE auth_session (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '登录会话主键',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '用户 ID',
    token_hash CHAR(64) NOT NULL COMMENT '访问令牌哈希',
    expires_at DATETIME NOT NULL COMMENT '过期时间',
    revoked_at DATETIME NULL COMMENT '注销时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_auth_session_token_hash (token_hash),
    KEY idx_auth_session_user (user_id),
    KEY idx_auth_session_expires_at (expires_at),
    CONSTRAINT fk_auth_session_user
        FOREIGN KEY (user_id) REFERENCES chefmate_user(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录会话表';

CREATE TABLE uploaded_asset (
    id CHAR(36) NOT NULL COMMENT '资源 ID',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '上传用户 ID',
    kind ENUM('image') NOT NULL COMMENT '资源类型',
    original_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    mime_type VARCHAR(128) NOT NULL COMMENT 'MIME 类型',
    storage_key VARCHAR(255) NOT NULL COMMENT '文件存储键',
    byte_size INT UNSIGNED NOT NULL COMMENT '文件大小',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_uploaded_asset_storage_key (storage_key),
    KEY idx_uploaded_asset_user (user_id),
    CONSTRAINT fk_uploaded_asset_user
        FOREIGN KEY (user_id) REFERENCES chefmate_user(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上传资源表';

CREATE TABLE conversation (
    id CHAR(36) NOT NULL COMMENT '对话 ID',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '所属用户 ID',
    title VARCHAR(120) NOT NULL COMMENT '对话标题',
    stage ENUM('idea', 'planning', 'shopping', 'cooking') NOT NULL DEFAULT 'idea' COMMENT '当前阶段',
    current_recipe_name VARCHAR(128) NULL COMMENT '当前菜名',
    suggestions_json JSON NOT NULL COMMENT '当前快捷建议列表',
    summary_text MEDIUMTEXT NULL COMMENT '对话压缩摘要',
    current_task_id CHAR(36) NULL COMMENT '当前活动任务 ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_conversation_user (user_id),
    KEY idx_conversation_updated_at (updated_at),
    CONSTRAINT fk_conversation_user
        FOREIGN KEY (user_id) REFERENCES chefmate_user(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户对话表';

CREATE TABLE conversation_task (
    id CHAR(36) NOT NULL COMMENT '任务 ID',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '所属用户 ID',
    conversation_id CHAR(36) NOT NULL COMMENT '所属对话 ID',
    stage ENUM('idea', 'planning', 'shopping', 'cooking') NOT NULL COMMENT '任务当前阶段',
    status ENUM('active', 'completed', 'cancelled') NOT NULL DEFAULT 'active' COMMENT '任务状态',
    outcome ENUM('completed', 'cancelled') NULL COMMENT '任务结束结果',
    source_recipe_id BIGINT UNSIGNED NULL COMMENT '若来自菜谱库，则记录源菜谱 ID',
    recipe_snapshot_json JSON NULL COMMENT '任务中的动态菜谱快照',
    record_in_history TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否纳入用户历史任务',
    ended_at DATETIME NULL COMMENT '结束时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_conversation_task_conversation (conversation_id),
    KEY idx_conversation_task_user_status (user_id, status),
    KEY idx_conversation_task_ended_at (ended_at),
    CONSTRAINT fk_conversation_task_user
        FOREIGN KEY (user_id) REFERENCES chefmate_user(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_conversation_task_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversation(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_conversation_task_source_recipe
        FOREIGN KEY (source_recipe_id) REFERENCES recipe(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话任务表';

CREATE TABLE conversation_message (
    id CHAR(36) NOT NULL COMMENT '消息 ID',
    conversation_id CHAR(36) NOT NULL COMMENT '所属对话 ID',
    task_id CHAR(36) NULL COMMENT '关联任务 ID',
    role ENUM('user', 'assistant', 'system') NOT NULL COMMENT '消息角色',
    content_md MEDIUMTEXT NOT NULL COMMENT 'Markdown 文本',
    suggestions_json JSON NULL COMMENT '本条消息更新后的 suggestions',
    card_type VARCHAR(64) NULL COMMENT '卡片类型',
    card_payload_json JSON NULL COMMENT '卡片结构',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_conversation_message_conversation (conversation_id, created_at),
    KEY idx_conversation_message_task (task_id),
    CONSTRAINT fk_conversation_message_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversation(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_conversation_message_task
        FOREIGN KEY (task_id) REFERENCES conversation_task(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话消息表';

CREATE TABLE conversation_message_attachment (
    message_id CHAR(36) NOT NULL COMMENT '消息 ID',
    asset_id CHAR(36) NOT NULL COMMENT '资源 ID',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '附件顺序',
    PRIMARY KEY (message_id, asset_id),
    KEY idx_conversation_message_attachment_asset (asset_id),
    CONSTRAINT fk_conversation_message_attachment_message
        FOREIGN KEY (message_id) REFERENCES conversation_message(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_conversation_message_attachment_asset
        FOREIGN KEY (asset_id) REFERENCES uploaded_asset(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息附件关联表';
