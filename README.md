<div align="center">
<img src="logo-256px-no-padding.png" />
<h1> https://tnyr.me - Privacy-First URL Shortener</h1>
</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A secure, self-hosted URL shortener with custom passwordless encryption. Perfect for privacy-conscious users and organizations.

![Screenshot](site-screenshot.png)

## Key Features

🔒 **Passwordless Encryption**  
📡 **No Tracking**   
🌐 **Modern Web Interface**  

## Encryption Process

1. **ID Generation**  
   - Unique random ID created for each link (e.g. `iA4y6jMjFk`)
   - Example: `google.com` → `tnyr.me/#iA4y6jMjFk`

2. **Hashing**  
   - Two Scrypt hashes are calculated by using different salts
   - Original URL encrypted with AES-256 using Hash 2
   - The whole encryption and decryption process happens in the browser

3. **Storage**  
   - Only Hash 1 (storage key) and the encrypted URL are saved in database

## Self Hosting and Development 

### Self-host (recommended): Docker / Docker Compose

#### Prerequisites
- Docker (and optionally Docker Compose)

#### 1) Generate salts (only if you hosted tnyr.me before **Dec 30, 2025**)

```bash
python3 backend/generate_salts.py --env
```

#### 2) Run with Docker Compose (no secrets required)

```bash
mkdir -p data
export TNYR_PUBLIC_URL=https://example.com  # (or http://1.2.3.4:5502)
docker compose up -d --build
```

Required env vars:
- `TNYR_PUBLIC_URL` (example `https://example.com`, `http://1.2.3.4:5502`)

Optional env vars:
- `TNYR_DB_PATH` (defaults to `/data/urls.db` in the container via compose)
- `TNYR_DELETION_TOKEN` (set to enable `POST /delete-url`)
- **Legacy link support (only if you hosted tnyr.me before Dec 30, 2025)**:
  - `TNYR_SALT1_HEX` (16 bytes = 32 hex chars)
  - `TNYR_SALT2_HEX` (16 bytes = 32 hex chars)
  - `TNYR_ARGON2_TIME_COST` (default `3`)
  - `TNYR_ARGON2_MEMORY_COST` (default `65536`)
  - `TNYR_ARGON2_PARALLELISM` (default `1`)
  - `TNYR_ARGON2_HASH_LENGTH` (default `32`)

**Note**: Creating new legacy links via `POST /shorten-server` is disabled. The legacy env vars above are only for resolving existing old `/<id>` links.

#### 3) Or run with plain Docker

```bash
docker build -t tnyr .
docker run --rm \
  -p 5502:5502 \
  -v "$PWD/data:/data" \
  -e TNYR_PUBLIC_URL="${TNYR_PUBLIC_URL:-http://localhost:5502}" \
  -e TNYR_DB_PATH="/data/urls.db" \
  tnyr
```

Then open `http://localhost:5502`.

**Note**: On container start, the entrypoint will initialize the SQLite schema (if missing) and replace `%VITE_PUBLIC_URL%` / `%VITE_DOMAIN%` placeholders in `backend/dist` based on `TNYR_PUBLIC_URL`.

### Development

1. **Start development server:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Start backend server:**
   ```bash
   cd backend
   pip install -r requirements.txt
   # Required:
   export TNYR_PUBLIC_URL=https://example.com
   # Optional (legacy server-side mode only):
   # export TNYR_SALT1_HEX=...  # 32 hex chars
   # export TNYR_SALT2_HEX=...  # 32 hex chars
   python main.py
   ```

## Why Choose [tnyr.me](https://tnyr.me)?

- **Privacy by Design**: We literally can't view your links
- **No Tracking**: Zero cookies, analytics, or fingerprinting
- **Self-Hostable**: Full control over your data
