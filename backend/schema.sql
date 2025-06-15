CREATE TABLE IF NOT EXISTS urls (
    lookup_hash TEXT PRIMARY KEY,
    iv BLOB NOT NULL,
    encrypted_url BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS client_side_urls (
    lookup_hash TEXT PRIMARY KEY,
    encryption_salt BLOB NOT NULL,
    iv BLOB NOT NULL,
    encrypted_url BLOB NOT NULL
);