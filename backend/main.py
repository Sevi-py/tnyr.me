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
    init_db()
    app.run(host='0.0.0.0', port=5000)