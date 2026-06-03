-- Add planning fields to the dive table.
-- Created: 2026-06-03

ALTER TABLE dive ADD COLUMN title TEXT;
ALTER TABLE dive ADD COLUMN join_policy TEXT NOT NULL DEFAULT 'open';
ALTER TABLE dive ADD COLUMN join_password_hash TEXT;
