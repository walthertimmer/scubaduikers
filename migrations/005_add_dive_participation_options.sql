-- Add participation_mode to UserDiveLink
ALTER TABLE userdivelink ADD COLUMN participation_mode TEXT;

-- Create ClubDiveOption table
CREATE TABLE IF NOT EXISTS clubdiveoption (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    label TEXT NOT NULL DEFAULT 'Hoe neem jij deel?',
    options TEXT NOT NULL DEFAULT '["Ik ga direct naar de duiklocatie", "Ik ga eerst naar het verzamelpunt en moet vullen", "Ik ga eerst naar het verzamelpunt maar hoef niet te vullen", "Ik kom maar ga niet duiken"]',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (club_id) REFERENCES divingclub(id) ON DELETE CASCADE
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_clubdiveoption_club_id ON clubdiveoption(club_id);
