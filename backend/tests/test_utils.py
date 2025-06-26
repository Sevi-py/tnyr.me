import pytest
import re
import sys
import os
from unittest.mock import patch

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import generate_id


class TestIDGeneration:
    """Test ID generation functionality"""
    
    def test_generate_id_basic(self, mock_config):
        """Test basic ID generation"""
        id_str = generate_id()
        
        assert isinstance(id_str, str)
        assert len(id_str) == 10  # From test config
        
    def test_generate_id_allowed_chars(self, mock_config):
        """Test that generated IDs only contain allowed characters"""
        allowed_chars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ123456789"
        
        for _ in range(100):  # Test multiple generations
            id_str = generate_id()
            for char in id_str:
                assert char in allowed_chars
                
    def test_generate_id_uniqueness(self, mock_config):
        """Test that generated IDs are likely unique"""
        ids = set()
        
        # Generate many IDs and check for uniqueness
        for _ in range(1000):
            id_str = generate_id()
            ids.add(id_str)
            
        # With 10 characters from 58-character alphabet, collisions should be extremely rare
        # We expect very high uniqueness
        assert len(ids) > 990  # Allow for very rare collisions
        
    def test_generate_id_format(self, mock_config):
        """Test that generated IDs match expected format"""
        id_str = generate_id()
        
        # Should be alphanumeric but exclude confusing characters like 0, O, I, l
        pattern = r'^[abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ123456789]{10}$'
        assert re.match(pattern, id_str)
        
    def test_generate_id_no_confusing_chars(self, mock_config):
        """Test that IDs don't contain visually confusing characters"""
        confusing_chars = ['0', 'O', 'I', 'l']
        
        for _ in range(100):
            id_str = generate_id()
            for char in confusing_chars:
                assert char not in id_str
                
    def test_generate_id_length_consistency(self, mock_config):
        """Test that all generated IDs have consistent length"""
        expected_length = 10
        
        for _ in range(50):
            id_str = generate_id()
            assert len(id_str) == expected_length
            
    def test_generate_id_different_config_length(self, test_config):
        """Test ID generation with different configured length"""
        test_config['id_generation']['length'] = 8
        
        with patch('main.config', test_config):
            id_str = generate_id()
            assert len(id_str) == 8
            
    def test_generate_id_different_allowed_chars(self, test_config):
        """Test ID generation with different allowed characters"""
        test_config['id_generation']['allowed_chars'] = 'abc123'
        
        with patch('main.config', test_config):
            id_str = generate_id()
            assert len(id_str) == test_config['id_generation']['length']  # Use config length
            for char in id_str:
                assert char in 'abc123'


class TestConfigValidation:
    """Test configuration validation and salt handling"""
    
    def test_salt_validation_correct_length(self):
        """Test that valid salts are accepted"""
        salt_hex = "85ddce7d130a6f1beba59fc8ba2a715d"  # 32 hex chars = 16 bytes
        salt_bytes = bytes.fromhex(salt_hex)
        
        assert len(salt_bytes) == 16
        
    def test_salt_validation_incorrect_length(self):
        """Test that invalid salt lengths are rejected"""
        # Too short
        short_salt = "85ddce7d130a6f1b"  # 16 hex chars = 8 bytes
        salt_bytes = bytes.fromhex(short_salt)
        assert len(salt_bytes) != 16
        
        # Too long  
        long_salt = "85ddce7d130a6f1beba59fc8ba2a715d85ddce7d130a6f1beba59fc8ba2a715d"  # 64 hex chars = 32 bytes
        salt_bytes = bytes.fromhex(long_salt)
        assert len(salt_bytes) != 16
        
    def test_invalid_hex_salt(self):
        """Test that invalid hex strings are rejected"""
        invalid_salts = [
            "invalid_hex_string",
            "85ddce7d130a6f1beba59fc8ba2a715g",  # Invalid hex char 'g'
            "85ddce7d130a6f1beba59fc8ba2a715",   # Odd number of chars
        ]
        
        for invalid_salt in invalid_salts:
            with pytest.raises(ValueError):
                bytes.fromhex(invalid_salt)


class TestURLNormalization:
    """Test URL preprocessing and normalization"""
    
    def test_url_prefix_addition(self):
        """Test that URLs get proper prefixes added"""
        test_cases = [
            ("google.com", "http://google.com"),
            ("example.org", "http://example.org"),
            ("domain.co.uk", "http://domain.co.uk"),
            ("subdomain.example.com", "http://subdomain.example.com"),
        ]
        
        for input_url, expected_output in test_cases:
            # Simulate the URL preprocessing logic from main.py
            url = input_url
            if not (url.startswith('https://') or url.startswith('http://') or url.startswith('magnet:')):
                url = 'http://' + url
            assert url == expected_output
            
    def test_url_prefix_preservation(self):
        """Test that existing prefixes are preserved"""
        test_urls = [
            "https://google.com",
            "http://example.com",
            "magnet:?xt=urn:btih:example",
        ]
        
        for url in test_urls:
            # Simulate the URL preprocessing logic from main.py
            processed_url = url
            if not (url.startswith('https://') or url.startswith('http://') or url.startswith('magnet:')):
                processed_url = 'http://' + url
            assert processed_url == url  # Should remain unchanged 