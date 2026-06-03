ALTER TABLE user ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0;
ALTER TABLE user ADD COLUMN verification_token TEXT;
ALTER TABLE user ADD COLUMN reset_token TEXT;
ALTER TABLE user ADD COLUMN reset_token_expires TEXT;
