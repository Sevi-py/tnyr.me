import os
import json
import sqlite3
import secrets
from flask import Flask, request, jsonify, redirect
from contextlib import closing
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from hashlib import scrypt as hashlib_scrypt

# --- Determine absolute path for file access ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, 'config.json')

# Load configuration
with open(CONFIG_PATH) as f:
    config = json.load(f)

# --- Make database path absolute ---
if not os.path.isabs(config['database']['path']):
    config['database']['path'] = os.path.join(APP_DIR, config['database']['path'])

app = Flask(__name__, static_folder='dist', static_url_path='/static')

# Validate and load salts
salt1_hex = config['salts']['salt1_var']
salt2_hex = config['salts']['salt2_var']

# Validate and convert salts
try:
    SALT1 = bytes.fromhex(salt1_hex)
    SALT2 = bytes.fromhex(salt2_hex)
    if len(SALT1) != 16 or len(SALT2) != 16:
        raise ValueError("Salts must decode to 16 bytes")
except ValueError as e:
    raise ValueError("Invalid salt format") from e

# Database setup
def get_db():
    conn = sqlite3.connect(config['database']['path'])
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    with closing(get_db()) as conn:
        with app.open_resource('schema.sql', mode='r') as f:
            conn.cursor().executescript(f.read())
        conn.commit()

# ID generation setup
def generate_id():
    """Generate random ID based on config"""
    return ''.join(
        secrets.choice(config['id_generation']['allowed_chars'])
        for _ in range(config['id_generation']['length'])
    )

# Argon2 configuration
def derive_key(id_bytes, salt):
    """Derive cryptographic key using Argon2 with config parameters"""
    return hash_secret_raw(
        secret=id_bytes,
        salt=salt,
        time_cost=config['argon2']['time_cost'],
        memory_cost=config['argon2']['memory_cost'],
        parallelism=config['argon2']['parallelism'],
        hash_len=config['argon2']['hash_length'],
        type=Type.ID
    )

def encrypt_url(key, plaintext):
    """Encrypt URL using AES-256-CBC"""
    # Validate key length
    if len(key) != 32:
        raise ValueError(f"Invalid key length: {len(key)} bytes (need 32)")
    
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode()) + padder.finalize()
    
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    return iv, ciphertext

def decrypt_url(key, iv, ciphertext):
    """Decrypt URL using AES-256-CBC"""
    if len(key) != 32:
        raise ValueError(f"Invalid key length: {len(key)} bytes (need 32)")
    
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    
    return plaintext.decode()

def hash_id_for_lookup_client(id_str):
    """Hash ID for lookup using the same method as the client (scrypt with LOOKUP_SALT)"""
    LOOKUP_SALT = bytes([0x74, 0x6e, 0x79, 0x72, 0x2e, 0x6d, 0x65, 0x5f, 0x6c, 0x6f, 0x6f, 0x6b, 0x75, 0x70, 0x5f, 0x73])
    
    # Use hashlib's scrypt with the same parameters as the frontend
    # Frontend uses: N: 2**17, r: 8, p: 1, dkLen: 32
    hash_result = hashlib_scrypt(
        password=id_str.encode(),
        salt=LOOKUP_SALT,
        n=2**17,
        r=8,
        p=1,
        dklen=32
    )
    return hash_result.hex()

def derive_encryption_key_client(id_str, salt):
    """Derive encryption key using the same method as the client (scrypt)"""
    # Use hashlib's scrypt with the same parameters as the frontend
    hash_result = hashlib_scrypt(
        password=id_str.encode(),
        salt=salt,
        n=2**17,
        r=8,
        p=1,
        dklen=32
    )
    return hash_result

def encrypt_url_client(key, plaintext):
    """Encrypt URL using the same method as the client (AES-CBC)"""
    if len(key) != 32:
        raise ValueError(f"Invalid key length: {len(key)} bytes (need 32)")
    
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode()) + padder.finalize()
    
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    return iv, ciphertext

ABUSE_WARNING_MARKER = '__ABUSE_WARNING__'

@app.route('/delete-url', methods=['POST'])
def delete_url():
    """Replace a URL with an abuse warning page (both old and new encryption methods)"""
    # Check if deletion is enabled
    deletion_token = config.get('deletion_token', '')
    if not deletion_token:
        return jsonify({"error": "URL deletion is disabled"}), 403
    
    data = request.get_json()
    
    if not data or 'id' not in data or 'deletion_token' not in data:
        return jsonify({"error": "Missing id or deletion_token"}), 400
    
    # Verify deletion token
    if data['deletion_token'] != deletion_token:
        return jsonify({"error": "Invalid deletion token"}), 403
    
    link_id = data['id']
    updated = False
    
    with get_db() as conn:
        # Try to update old server-side encrypted URLs table
        id_bytes = link_id.encode()
        lookup_hash_old = derive_key(id_bytes, SALT1).hex()
        
        # Check if it exists in old table
        cur = conn.execute(
            "SELECT 1 FROM urls WHERE lookup_hash = ?",
            (lookup_hash_old,)
        )
        if cur.fetchone():
            # Re-encrypt the abuse marker using server-side method
            encryption_key = derive_key(id_bytes, SALT2)
            iv, encrypted_warning = encrypt_url(encryption_key, ABUSE_WARNING_MARKER)
            
            conn.execute(
                "UPDATE urls SET iv = ?, encrypted_url = ? WHERE lookup_hash = ?",
                (iv, encrypted_warning, lookup_hash_old)
            )
            conn.commit()
            updated = True
        
        # If not found, try to update new client-side encrypted URLs table
        if not updated:
            lookup_hash_new = hash_id_for_lookup_client(link_id)
            
            # Check if it exists in new table
            cur = conn.execute(
                "SELECT 1 FROM client_side_urls WHERE lookup_hash = ?",
                (lookup_hash_new,)
            )
            if cur.fetchone():
                # Re-encrypt the abuse marker using client-side method
                # Generate new encryption salt (since original was random)
                new_encryption_salt = os.urandom(16)
                encryption_key = derive_encryption_key_client(link_id, new_encryption_salt)
                iv, encrypted_warning = encrypt_url_client(encryption_key, ABUSE_WARNING_MARKER)
                
                conn.execute(
                    "UPDATE client_side_urls SET encryption_salt = ?, iv = ?, encrypted_url = ? WHERE lookup_hash = ?",
                    (new_encryption_salt, iv, encrypted_warning, lookup_hash_new)
                )
                conn.commit()
                updated = True
    
    if updated:
        return jsonify({"message": "URL replaced with abuse warning successfully"}), 200
    else:
        return jsonify({"error": "Link not found"}), 404

@app.route('/shorten-server', methods=['POST'])
def shorten_url_server():
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({"error": "Missing URL"}), 400
    
    id = None
    url = data['url']

    if not (url.startswith('https://') or url.startswith('http://') or url.startswith('magnet:')):
        url = 'http://' + url

    with get_db() as conn:
        # Generate unique ID and hash
        for _ in range(100):  # Retry limit
            id = generate_id()
            id_bytes = id.encode()
            
            # Derive lookup hash
            lookup_hash = derive_key(id_bytes, SALT1).hex()
            
            # Check for collision
            cur = conn.execute(
                "SELECT 1 FROM urls WHERE lookup_hash = ?",
                (lookup_hash,)
            )
            if not cur.fetchone():
                break
        else:
            return jsonify({"error": "Failed to generate unique ID"}), 500
        
        # Derive encryption key
        encryption_key = derive_key(id_bytes, SALT2)
        
        # Encrypt URL
        iv, encrypted_url = encrypt_url(encryption_key, url)
        
        # Store in database
        conn.execute(
            "INSERT INTO urls (lookup_hash, iv, encrypted_url) VALUES (?, ?, ?)",
            (lookup_hash, iv, encrypted_url)
        )
        conn.commit()
    
    return jsonify({"id": id}), 201

@app.route('/shorten', methods=['POST'])
def shorten_url_client():
    data = request.get_json()
    required_fields = ['LOOKUP_HASH', 'ENCRYTION_SALT', 'IV', 'ENCRYPTED_URL']

    if not data or not all(field in data for field in required_fields):
        missing_fields = [field for field in required_fields if field not in (data or {})]
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    lookup_hash = data['LOOKUP_HASH']
    
    try:
        encryption_salt = bytes.fromhex(data['ENCRYTION_SALT'])
        iv = bytes.fromhex(data['IV'])
        encrypted_url = bytes.fromhex(data['ENCRYPTED_URL'])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid hex format for salt, IV, or encrypted URL"}), 400

    with get_db() as conn:
        cur = conn.execute(
            "SELECT 1 FROM client_side_urls WHERE lookup_hash = ?",
            (lookup_hash,)
        )
        if cur.fetchone():
            return jsonify({"error": "Lookup hash already exists"}), 409
        
        conn.execute(
            "INSERT INTO client_side_urls (lookup_hash, encryption_salt, iv, encrypted_url) VALUES (?, ?, ?, ?)",
            (lookup_hash, encryption_salt, iv, encrypted_url)
        )
        conn.commit()

    return jsonify({"message": "URL shortened successfully"}), 201

@app.route('/get-encrypted-url', methods=['GET'])
def get_encrypted_url():
    lookup_hash = request.args.get('lookup_hash')

    if not lookup_hash:
        return jsonify({"error": "Missing lookup_hash parameter"}), 400

    with get_db() as conn:
        cur = conn.execute(
            "SELECT encryption_salt, iv, encrypted_url FROM client_side_urls WHERE lookup_hash = ?",
            (lookup_hash,)
        )
        row = cur.fetchone()

    if not row:
        return jsonify({"error": "Link not found"}), 404

    return jsonify({
        "ENCRYTION_SALT": row['encryption_salt'].hex(),
        "IV": row['iv'].hex(),
        "ENCRYPTED_URL": row['encrypted_url'].hex()
    }), 200

@app.route('/<id>') # Still needed for old links
def redirect_url(id):
    id_bytes = id.encode()
    
    # Derive lookup hash
    lookup_hash = derive_key(id_bytes, SALT1).hex()
    
    # Retrieve from database
    with get_db() as conn:
        cur = conn.execute(
            "SELECT iv, encrypted_url FROM urls WHERE lookup_hash = ?",
            (lookup_hash,)
        )
        row = cur.fetchone()
    
    if not row:
        return jsonify({"error": "Link not found"}), 404
    
    # Derive decryption key
    decryption_key = derive_key(id_bytes, SALT2)
    
    # Decrypt URL
    try:
        url = decrypt_url(decryption_key, row['iv'], row['encrypted_url'])
    except Exception as e:
        return jsonify({"error": "Decryption failed"}), 500
    
    # Check if this is an abuse warning
    if url == ABUSE_WARNING_MARKER:
        # Redirect to home page with abuse warning hash
        domain = config.get('domain', {}).get('name', 'tnyr.me')
        abuse_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <meta name="googlebot" content="noindex, nofollow">
    <title>Link Removed - Abuse Detected</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #9333ea 0%, #7e22ce 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 2rem 3rem;
            max-width: 700px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #dc2626;
            margin-top: 0;
            font-size: 28px;
        }}
        .warning-icon {{
            font-size: 64px;
            text-align: center;
            margin-bottom: 20px;
        }}
        p {{
            color: #374151;
            line-height: 1.6;
            margin: 15px 0;
        }}
        .alert-box {{
            background: #fef2f2;
            border-left: 4px solid #dc2626;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .info-box {{
            background: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        ul {{
            color: #374151;
            line-height: 1.8;
        }}
        li {{
            margin: 8px 0;
        }}
        strong {{
            color: #1f2937;
        }}
        a {{
            color: #2563eb;
            text-decoration: underline;
        }}
        a:hover {{
            color: #1d4ed8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="warning-icon">⚠️</div>
        <h1>This Link Has Been Removed</h1>
        
        <div class="alert-box">
            <p><strong>This shortened URL has been disabled due to abuse reports.</strong></p>
        </div>
        
        <p>The link you followed has been removed from our service because it was reported for one or more of the following reasons:</p>
        
        <ul>
            <li>Phishing or scam attempt</li>
            <li>Malware distribution</li>
            <li>Fraudulent content</li>
            <li>Harassment or threats</li>
            <li>Other malicious activity</li>
        </ul>
        
        <div class="info-box">
            <p><strong>⚠️ Important Security Reminders:</strong></p>
            <ul>
                <li>Never share personal information, passwords, or financial details through untrusted links</li>
                <li>Be cautious of urgent messages claiming your account will be locked or money is owed</li>
                <li>Verify the authenticity of communications by contacting organizations directly through official channels</li>
                <li>Legitimate companies will never ask for sensitive information via email or text messages</li>
                <li>If something seems too good to be true, it probably is</li>
            </ul>
        </div>
        
        <p style="text-align: center; font-size: 14px;">
            <strong>If you believe this link was removed in error, please contact us at <a href="mailto:abuse@{domain}">abuse@{domain}</a></strong>
        </p>
    </div>
</body>
</html>"""
        return abuse_html, 200
    
    return redirect(url, code=302)

@app.route('/')
def serve_react_app():
    return app.send_static_file('index.html')

@app.route("/robots.txt")
def serve_robots_txt():
    return app.send_static_file("meta/robots.txt")

@app.route("/sitemap.xml")
def serve_sitemap_xml():
    return app.send_static_file("meta/sitemap.xml")

@app.route('/<path:path>')
def serve_static_files(path):
    return app.send_static_file(path)

if __name__ == '__main__':
    # Enable permissive CORS for development
    @app.before_request
    def _cors_handle_preflight():
        if request.method == 'OPTIONS':
            response = app.make_default_options_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            requested_headers = request.headers.get('Access-Control-Request-Headers', '')
            if requested_headers:
                response.headers['Access-Control-Allow-Headers'] = requested_headers
            else:
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Max-Age'] = '86400'
            return response

    @app.after_request
    def _cors_add_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        # Keep this broad for dev; browsers will ignore extras if not needed
        if 'Access-Control-Allow-Headers' not in response.headers:
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    init_db()
    app.run(host='0.0.0.0', port=5000)