-- Migration: Simplify dive model - single location field, remove DiveSite
-- For SQLite: must recreate table to remove column with FK constraint

BEGIN TRANSACTION;

-- Step 1: Add location column to dive table
ALTER TABLE dive ADD COLUMN location TEXT NOT NULL DEFAULT '';

-- Step 2: Create temporary table without site_id column
CREATE TABLE dive_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    title TEXT,
    location TEXT NOT NULL,
    description TEXT,
    organiser_club_id INTEGER,
    organiser_user_id INTEGER,
    join_policy TEXT NOT NULL DEFAULT 'open',
    join_password_hash TEXT,
    FOREIGN KEY (organiser_club_id) REFERENCES divingclub(id),
    FOREIGN KEY (organiser_user_id) REFERENCES user(id)
);

-- Step 3: Copy all data (excluding site_id) to new table
INSERT INTO dive_new (id, date, title, location, description, organiser_club_id, organiser_user_id, join_policy, join_password_hash)
SELECT id, date, title, location, description, organiser_club_id, organiser_user_id, join_policy, join_password_hash FROM dive;

-- Step 4: Drop old dive table
DROP TABLE dive;

-- Step 5: Rename new table to dive
ALTER TABLE dive_new RENAME TO dive;

-- Step 6: Recreate indexes
CREATE INDEX IF NOT EXISTS idx_dive_date ON dive(date);
CREATE INDEX IF NOT EXISTS idx_dive_organiser_club_id ON dive(organiser_club_id);
CREATE INDEX IF NOT EXISTS idx_dive_organiser_user_id ON dive(organiser_user_id);
CREATE INDEX IF NOT EXISTS idx_dive_join_policy ON dive(join_policy);

-- Step 7: Drop the divesite table
DROP TABLE divesite;

COMMIT;
