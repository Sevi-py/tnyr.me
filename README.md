<div align="center">
<img src="logo-256px-no-padding.png" />
<h1> https://tnyr.me - Privacy-First URL Shortener</h1>
</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A secure, self-hosted URL shortener with end-to-end encryption. Perfect for privacy-conscious users and organizations.

![Screenshot](site-screenshot.png)

## Key Features

🔒 **Passwordless end-to-end Encryption**  
📡 **No Tracking**   
🌐 **Modern Web Interface**  

## end-to-end Encryption Process

1. **ID Generation**  
   - Unique random ID created for each link (e.g. `iA4y6jMjFk`)
   - Example: `google.com` → `tnyr.me/#iA4y6jMjFk`

2. **Hashing**  
   - Two Scrypt hashes are calculated by using different salts
   - Original URL encrypted with AES-256 using Hash 2
   - The whole encryption and decryption process happens in the browser

3. **Storage**  
   - Only Hash 1 (storage key) and the encrypted URL are saved in database

## Development Setup

### Prerequisites
- Python 3.9+
- Node.js 16+ (for frontend development)

### Quick Start
1. **Clone Repository**
   ```bash
   git clone https://github.com/sevi-py/tnyr.me.git
   cd tnyr/backend
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration**  
   Rename `config_template.json` to `config.json`  
   Generate salts using `python generate_salts.py`  
   Replace the placeholders with the salts you generated  

4. **Start Server**
   ```bash
   python main.py
   ```

5. Access at `http://localhost:5000`

## Frontend Development
The backend serves pre-built frontend files. To modify the frontend:

```bash
cd frontend
npm install
npm run build
```

## Why Choose [tnyr.me](https://tnyr.me)?

- **Privacy by Design**: We literally can't view your links
- **No Tracking**: Zero cookies, analytics, or fingerprinting
- **Self-Hostable**: Full control over your data