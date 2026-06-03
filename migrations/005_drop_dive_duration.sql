-- Remove duration from the dive table (column no longer in the model).
-- SQLite 3.35+ required for DROP COLUMN.
-- Created: 2026-06-03

ALTER TABLE dive DROP COLUMN duration;
