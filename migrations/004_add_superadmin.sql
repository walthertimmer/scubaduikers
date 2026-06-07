-- Add is_superadmin flag to user table
-- Created: 2026-06-07

ALTER TABLE user ADD COLUMN is_superadmin BOOLEAN NOT NULL DEFAULT 0;
