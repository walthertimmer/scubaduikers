CREATE TABLE IF NOT EXISTS divecomment (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    dive_id    INTEGER NOT NULL REFERENCES dive(id),
    user_id    INTEGER NOT NULL REFERENCES user(id),
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
