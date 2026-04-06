USE chefmate;

ALTER TABLE chefmate_user
    ADD COLUMN voice_wake_word_enabled TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否开启命令词唤醒' AFTER profile_completed_at,
    ADD COLUMN voice_wake_word_prompted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已经询问过命令词唤醒' AFTER voice_wake_word_enabled;
