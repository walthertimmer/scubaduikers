-- Rename notes -> description on the dive table.
-- Created: 2026-06-03

ALTER TABLE dive RENAME COLUMN notes TO description;
