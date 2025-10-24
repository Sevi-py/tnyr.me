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

### Prerequisites
- Python 3.9+
- Node.js 16+

### Instructions

1. **Deploy with your domain:**
   ```bash
   ./deploy.sh your-domain.com
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup the config:**
   ```bash
   cp config_template.json config.json
   python generate_salts.py
   ```
   You will see two salts, which you can use in the config.

4. **Start Server**
   ```bash
   python main.py
   ```

5. Access at `http://localhost:5000`

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
   python main.py
   ```

## Why Choose [tnyr.me](https://tnyr.me)?

- **Privacy by Design**: We literally can't view your links
- **No Tracking**: Zero cookies, analytics, or fingerprinting
- **Self-Hostable**: Full control over your data
