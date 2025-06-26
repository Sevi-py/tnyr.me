import os
import tempfile
import pytest
import sqlite3
import sys
from unittest.mock import patch
import json

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration to avoid using production config
TEST_CONFIG = {
    "salts": {
        "salt1_var": "11111111111111111111111111111111",
        "salt2_var": "22222222222222222222222222222222"
    },
    "argon2": {
        "time_cost": 1,  # Reduced for faster tests
        "memory_cost": 1024,  # Reduced for faster tests
        "parallelism": 1,
        "hash_length": 32
    },
    "database": {
        "path": ":memory:"  # In-memory database for tests
    },
    "id_generation": {
        "length": 10,
        "allowed_chars": "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ123456789"
    }
}

@pytest.fixture(scope='function')
def test_config():
    """Provide test configuration"""
    return TEST_CONFIG.copy()

@pytest.fixture(scope='function')
def mock_config(test_config):
    """Mock the config loading in main.py"""
    with patch('main.config', test_config):
        with patch('main.SALT1', bytes.fromhex(test_config['salts']['salt1_var'])):
            with patch('main.SALT2', bytes.fromhex(test_config['salts']['salt2_var'])):
                yield test_config

@pytest.fixture(scope='function')
def app(mock_config):
    """Create and configure a test Flask app"""
    # Import after mocking config
    from main import app, init_db
    
    app.config.update({
        "TESTING": True,
    })
    
    # Mock get_db to use in-memory database
    with patch('main.get_db') as mock_get_db:
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        
        # Create schema using absolute path
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema.sql')
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        
        mock_get_db.return_value = conn
        
        with app.app_context():
            yield app
            
        conn.close()

@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the Flask app"""
    return app.test_client()

@pytest.fixture(scope='function')
def test_db_connection(mock_config):
    """Provide a test database connection"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Create schema using absolute path
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema.sql')
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    
    yield conn
    conn.close()

@pytest.fixture
def sample_urls():
    """Provide sample URLs for testing"""
    return [
        "https://google.com",
        "http://example.com",
        "https://github.com/user/repo",
        "magnet:?xt=urn:btih:example",
        "domain.com",  # Should get http:// prefix
    ]

@pytest.fixture
def sample_encrypted_data():
    """Provide sample encrypted data for testing"""
    return {
        "LOOKUP_HASH": "abcd1234efgh5678",
        "ENCRYTION_SALT": "11111111111111111111111111111111",
        "IV": "22222222222222222222222222222222",
        "ENCRYPTED_URL": "33333333333333333333333333333333"
    } 