import pytest
import os
import sys
from unittest.mock import patch

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import encrypt_url, decrypt_url, derive_key
from argon2.low_level import Type


class TestCryptographicFunctions:
    """Test all cryptographic functions for security and correctness"""
    
    def test_derive_key_basic(self, mock_config):
        """Test basic key derivation functionality"""
        id_bytes = b"test_id"
        salt = bytes.fromhex("11111111111111111111111111111111")
        
        key = derive_key(id_bytes, salt)
        
        assert len(key) == 32  # Should be 32 bytes for AES-256
        assert isinstance(key, bytes)
        
    def test_derive_key_deterministic(self, mock_config):
        """Test that key derivation is deterministic"""
        id_bytes = b"test_id"
        salt = bytes.fromhex("11111111111111111111111111111111")
        
        key1 = derive_key(id_bytes, salt)
        key2 = derive_key(id_bytes, salt)
        
        assert key1 == key2
        
    def test_derive_key_different_inputs_different_outputs(self, mock_config):
        """Test that different inputs produce different keys"""
        salt = bytes.fromhex("11111111111111111111111111111111")
        
        key1 = derive_key(b"id1", salt)
        key2 = derive_key(b"id2", salt)
        key3 = derive_key(b"id1", bytes.fromhex("22222222222222222222222222222222"))
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
        
    def test_encrypt_url_basic(self):
        """Test basic URL encryption"""
        key = os.urandom(32)
        plaintext = "https://example.com"
        
        iv, ciphertext = encrypt_url(key, plaintext)
        
        assert len(iv) == 16  # AES block size
        assert len(ciphertext) > 0
        assert isinstance(iv, bytes)
        assert isinstance(ciphertext, bytes)
        
    def test_encrypt_url_invalid_key_length(self):
        """Test encryption with invalid key length"""
        invalid_key = os.urandom(16)  # Wrong length
        plaintext = "https://example.com"
        
        with pytest.raises(ValueError, match="Invalid key length"):
            encrypt_url(invalid_key, plaintext)
            
    def test_decrypt_url_basic(self):
        """Test basic URL decryption"""
        key = os.urandom(32)
        original_url = "https://example.com"
        
        iv, ciphertext = encrypt_url(key, original_url)
        decrypted_url = decrypt_url(key, iv, ciphertext)
        
        assert decrypted_url == original_url
        
    def test_decrypt_url_invalid_key_length(self):
        """Test decryption with invalid key length"""
        key = os.urandom(32)
        original_url = "https://example.com"
        
        iv, ciphertext = encrypt_url(key, original_url)
        invalid_key = os.urandom(16)  # Wrong length
        
        with pytest.raises(ValueError, match="Invalid key length"):
            decrypt_url(invalid_key, iv, ciphertext)
            
    def test_encrypt_decrypt_roundtrip(self):
        """Test complete encryption/decryption roundtrip"""
        key = os.urandom(32)
        test_urls = [
            "https://google.com",
            "http://example.com/path?param=value",
            "https://github.com/user/repo/issues/123",
            "magnet:?xt=urn:btih:example123456789",
            "https://very-long-domain-name.example.com/very/long/path/with/many/segments?lots=of&query=parameters&more=stuff"
        ]
        
        for url in test_urls:
            iv, ciphertext = encrypt_url(key, url)
            decrypted_url = decrypt_url(key, iv, ciphertext)
            assert decrypted_url == url
            
    def test_encrypt_same_url_different_iv(self):
        """Test that encrypting the same URL twice produces different ciphertexts (due to random IV)"""
        key = os.urandom(32)
        url = "https://example.com"
        
        iv1, ciphertext1 = encrypt_url(key, url)
        iv2, ciphertext2 = encrypt_url(key, url)
        
        assert iv1 != iv2
        assert ciphertext1 != ciphertext2
        
        # But both should decrypt to the same URL
        assert decrypt_url(key, iv1, ciphertext1) == url
        assert decrypt_url(key, iv2, ciphertext2) == url
        
    def test_decrypt_wrong_key(self):
        """Test decryption with wrong key fails appropriately"""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        url = "https://example.com"
        
        iv, ciphertext = encrypt_url(key1, url)
        
        with pytest.raises(Exception):  # Could be various crypto exceptions
            decrypt_url(key2, iv, ciphertext)
            
    def test_decrypt_corrupted_iv(self):
        """Test decryption with corrupted IV fails"""
        key = os.urandom(32)
        url = "https://example.com"
        
        iv, ciphertext = encrypt_url(key, url)
        corrupted_iv = os.urandom(16)  # Different IV
        
        with pytest.raises(Exception):
            decrypt_url(key, corrupted_iv, ciphertext)
            
    def test_decrypt_corrupted_ciphertext(self):
        """Test decryption with corrupted ciphertext fails"""
        key = os.urandom(32)
        url = "https://example.com"
        
        iv, ciphertext = encrypt_url(key, url)
        corrupted_ciphertext = os.urandom(len(ciphertext))
        
        with pytest.raises(Exception):
            decrypt_url(key, iv, corrupted_ciphertext)
            
    def test_unicode_url_handling(self):
        """Test handling of Unicode characters in URLs"""
        key = os.urandom(32)
        unicode_url = "https://example.com/测试/ñoño?查询=参数"
        
        iv, ciphertext = encrypt_url(key, unicode_url)
        decrypted_url = decrypt_url(key, iv, ciphertext)
        
        assert decrypted_url == unicode_url
        
    def test_empty_url_handling(self):
        """Test handling of edge case inputs"""
        key = os.urandom(32)
        
        # Empty string
        iv, ciphertext = encrypt_url(key, "")
        decrypted_url = decrypt_url(key, iv, ciphertext)
        assert decrypted_url == ""
        
        # Very short URL
        short_url = "a"
        iv, ciphertext = encrypt_url(key, short_url)
        decrypted_url = decrypt_url(key, iv, ciphertext)
        assert decrypted_url == short_url
        
    def test_key_derivation_with_production_config(self):
        """Test key derivation matches expected behavior with actual config values"""
        # This test uses more realistic Argon2 parameters
        from argon2.low_level import hash_secret_raw, Type
        
        id_bytes = b"testid1234"
        salt = bytes.fromhex("85ddce7d130a6f1beba59fc8ba2a715d")
        
        key = hash_secret_raw(
            secret=id_bytes,
            salt=salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
            type=Type.ID
        )
        
        assert len(key) == 32
        assert isinstance(key, bytes)
        # Key should be deterministic
        key2 = hash_secret_raw(
            secret=id_bytes,
            salt=salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
            type=Type.ID
        )
        assert key == key2 