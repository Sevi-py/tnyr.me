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

# Load configuration
with open('config.json') as f:
    config = json.load(f)

app = Flask(__name__, static_folder='dist', static_url_path='/static')

# Validate and load salts
salt1_hex = os.environ[config['environment']['salt1_var']]
salt2_hex = os.environ[config['environment']['salt2_var']]

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

@app.route('/shorten', methods=['POST'])
def shorten_url():
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
        print(f"Encryption key length: {len(encryption_key)} bytes")  # Debug
        
        # Encrypt URL
        iv, encrypted_url = encrypt_url(encryption_key, url)
        
        # Store in database
        conn.execute(
            "INSERT INTO urls (lookup_hash, iv, encrypted_url) VALUES (?, ?, ?)",
            (lookup_hash, iv, encrypted_url)
        )
        conn.commit()
    
    return jsonify({"id": id}), 201

@app.route('/<id>')
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
    print(f"Decryption key length: {len(decryption_key)} bytes")  # Debug
    
    # Decrypt URL
    try:
        url = decrypt_url(decryption_key, row['iv'], row['encrypted_url'])
    except Exception as e:
        return jsonify({"error": "Decryption failed"}), 500
    
    return redirect(url, code=302)

@app.route('/')
def serve_react_app():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return app.send_static_file(path)

# Configure Flask to serve the React app's static files
#app = Flask(__name__, )

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)