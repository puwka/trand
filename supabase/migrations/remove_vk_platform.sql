-- Remove VK from platform_enum (для существующих БД)
-- Сначала удалите или обновите источники с platform=vk:
--   DELETE FROM sources WHERE platform = 'vk';
-- или: UPDATE sources SET platform = 'tiktok' WHERE platform = 'vk';
-- Затем выполните этот скрипт в SQL Editor Supabase
ALTER TYPE platform_enum RENAME TO platform_enum_old;
CREATE TYPE platform_enum AS ENUM ('tiktok', 'reels', 'shorts');
ALTER TABLE sources ALTER COLUMN platform TYPE platform_enum USING platform::text::platform_enum;
DROP TYPE platform_enum_old;
