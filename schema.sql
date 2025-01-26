CREATE TABLE IF NOT EXISTS urls (
    lookup_hash TEXT PRIMARY KEY,
    iv BLOB NOT NULL,
    encrypted_url BLOB NOT NULL
);