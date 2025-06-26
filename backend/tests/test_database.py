import pytest
import sqlite3
import os
import sys
from contextlib import closing
from unittest.mock import patch

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import get_db, init_db


class TestDatabaseOperations:
    """Test database operations and schema"""
    
    def test_database_schema_creation(self, test_db_connection):
        """Test that the database schema is created correctly"""
        conn = test_db_connection
        
        # Check that both tables exist
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('urls', 'client_side_urls')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'urls' in tables
        assert 'client_side_urls' in tables
        
    def test_urls_table_structure(self, test_db_connection):
        """Test the structure of the urls table"""
        conn = test_db_connection
        
        cursor = conn.execute("PRAGMA table_info(urls)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'lookup_hash' in columns
        assert 'iv' in columns
        assert 'encrypted_url' in columns
        assert columns['lookup_hash'] == 'TEXT'
        assert columns['iv'] == 'BLOB'
        assert columns['encrypted_url'] == 'BLOB'
        
    def test_client_side_urls_table_structure(self, test_db_connection):
        """Test the structure of the client_side_urls table"""
        conn = test_db_connection
        
        cursor = conn.execute("PRAGMA table_info(client_side_urls)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'lookup_hash' in columns
        assert 'encryption_salt' in columns
        assert 'iv' in columns
        assert 'encrypted_url' in columns
        assert columns['lookup_hash'] == 'TEXT'
        assert columns['encryption_salt'] == 'BLOB'
        assert columns['iv'] == 'BLOB'
        assert columns['encrypted_url'] == 'BLOB'
        
    def test_primary_key_constraints(self, test_db_connection):
        """Test that primary key constraints work correctly"""
        conn = test_db_connection
        
        # Test urls table primary key
        conn.execute("""
            INSERT INTO urls (lookup_hash, iv, encrypted_url) 
            VALUES ('test_hash', ?, ?)
        """, (b'\x12\x34\x56\x78\x90\xab\xcd\xef', b'\xfe\xdc\xba\x09\x87\x65\x43\x21'))
        
        # Attempting to insert duplicate lookup_hash should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO urls (lookup_hash, iv, encrypted_url) 
                VALUES ('test_hash', ?, ?)
            """, (b'\xab\xcd', b'\xef\xab'))
            
        # Test client_side_urls table primary key
        conn.execute("""
            INSERT INTO client_side_urls (lookup_hash, encryption_salt, iv, encrypted_url) 
            VALUES ('client_hash', ?, ?, ?)
        """, (b'salt123', b'iv123', b'url123'))
        
        # Attempting to insert duplicate lookup_hash should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO client_side_urls (lookup_hash, encryption_salt, iv, encrypted_url) 
                VALUES ('client_hash', ?, ?, ?)
            """, (b'salt456', b'iv456', b'url456'))
            
    def test_not_null_constraints(self, test_db_connection):
        """Test that NOT NULL constraints are enforced"""
        conn = test_db_connection
        
        # Test urls table NOT NULL constraints
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO urls (lookup_hash, iv, encrypted_url) 
                VALUES ('test', NULL, ?)
            """, (b'encrypted',))
            
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO urls (lookup_hash, iv, encrypted_url) 
                VALUES ('test', ?, NULL)
            """, (b'iv',))
            
        # Test client_side_urls table NOT NULL constraints
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO client_side_urls (lookup_hash, encryption_salt, iv, encrypted_url) 
                VALUES ('test', NULL, ?, ?)
            """, (b'iv', b'url'))
            
    def test_data_insertion_and_retrieval(self, test_db_connection):
        """Test basic data insertion and retrieval"""
        conn = test_db_connection
        
        # Test urls table
        test_data = {
            'lookup_hash': 'test_lookup_hash',
            'iv': b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            'encrypted_url': b'\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8'
        }
        
        conn.execute("""
            INSERT INTO urls (lookup_hash, iv, encrypted_url) 
            VALUES (?, ?, ?)
        """, (test_data['lookup_hash'], test_data['iv'], test_data['encrypted_url']))
        
        cursor = conn.execute("""
            SELECT lookup_hash, iv, encrypted_url FROM urls 
            WHERE lookup_hash = ?
        """, (test_data['lookup_hash'],))
        
        row = cursor.fetchone()
        assert row is not None
        assert row['lookup_hash'] == test_data['lookup_hash']
        assert row['iv'] == test_data['iv']
        assert row['encrypted_url'] == test_data['encrypted_url']
        
    def test_blob_data_integrity(self, test_db_connection):
        """Test that BLOB data maintains integrity"""
        conn = test_db_connection
        
        # Test with various byte patterns
        test_cases = [
            b'\x00' * 16,  # All zeros
            b'\xff' * 16,  # All ones
            b'\x00\xff\x00\xff' * 4,  # Alternating pattern
            bytes(range(16)),  # Sequential bytes
            b'\x80\x00\x01\x7f' * 4,  # Edge values
        ]
        
        for i, test_bytes in enumerate(test_cases):
            lookup_hash = f'test_blob_{i}'
            conn.execute("""
                INSERT INTO urls (lookup_hash, iv, encrypted_url) 
                VALUES (?, ?, ?)
            """, (lookup_hash, test_bytes, test_bytes))
            
            cursor = conn.execute("""
                SELECT iv, encrypted_url FROM urls WHERE lookup_hash = ?
            """, (lookup_hash,))
            
            row = cursor.fetchone()
            assert row['iv'] == test_bytes
            assert row['encrypted_url'] == test_bytes
            
    def test_concurrent_access(self, test_db_connection):
        """Test handling of concurrent database access patterns"""
        conn = test_db_connection
        
        # Simulate concurrent inserts (sequential in test, but tests the pattern)
        for i in range(10):
            lookup_hash = f'concurrent_test_{i}'
            conn.execute("""
                INSERT INTO urls (lookup_hash, iv, encrypted_url) 
                VALUES (?, ?, ?)
            """, (lookup_hash, b'test_iv', b'test_url'))
            
        # Verify all records were inserted
        cursor = conn.execute("""
            SELECT COUNT(*) FROM urls WHERE lookup_hash LIKE 'concurrent_test_%'
        """)
        count = cursor.fetchone()[0]
        assert count == 10
        
    @patch('main.config')
    def test_get_db_with_file_database(self, mock_config):
        """Test get_db function with file-based database"""
        # Create a temporary database file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
            
        try:
            mock_config.return_value = {'database': {'path': db_path}}
            
            # Mock the config in main module
            with patch('main.config', {'database': {'path': db_path}}):
                conn = get_db()
                assert conn is not None
                
                # Test that row_factory is set correctly
                assert conn.row_factory == sqlite3.Row
                
                conn.close()
                
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)
                
    def test_init_db_functionality(self, mock_config):
        """Test that init_db creates the schema correctly"""
        # Create a temporary database file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
            
        try:
            # Mock config to use our temporary database
            with patch('main.config', {'database': {'path': db_path}}):
                init_db()
                
                # Verify the database was created with correct schema
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                
                # Check tables exist
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('urls', 'client_side_urls')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                assert 'urls' in tables
                assert 'client_side_urls' in tables
                
                conn.close()
                
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)
                
    def test_database_performance_basic(self, test_db_connection):
        """Test basic database performance characteristics"""
        import time
        conn = test_db_connection
        
        # Test insertion performance
        start_time = time.time()
        for i in range(100):
            conn.execute("""
                INSERT INTO urls (lookup_hash, iv, encrypted_url) 
                VALUES (?, ?, ?)
            """, (f'perf_test_{i}', b'test_iv' * 2, b'test_url' * 4))
        insertion_time = time.time() - start_time
        
        # Test query performance
        start_time = time.time()
        for i in range(100):
            cursor = conn.execute("""
                SELECT iv, encrypted_url FROM urls WHERE lookup_hash = ?
            """, (f'perf_test_{i}',))
            cursor.fetchone()
        query_time = time.time() - start_time
        
        # Basic performance assertions (should be very fast for 100 operations)
        assert insertion_time < 1.0  # Should complete in under 1 second
        assert query_time < 1.0     # Should complete in under 1 second
        
    def test_data_types_validation(self, test_db_connection):
        """Test that correct data types are handled properly"""
        conn = test_db_connection
        
        # Test TEXT data
        long_text = 'a' * 1000  # 1KB text
        conn.execute("""
            INSERT INTO urls (lookup_hash, iv, encrypted_url) 
            VALUES (?, ?, ?)
        """, (long_text, b'test_iv', b'test_url'))
        
        cursor = conn.execute("""
            SELECT lookup_hash FROM urls WHERE lookup_hash = ?
        """, (long_text,))
        row = cursor.fetchone()
        assert row['lookup_hash'] == long_text
        
        # Test BLOB data of various sizes
        blob_sizes = [1, 16, 256, 1024, 4096]  # Various sizes
        for size in blob_sizes:
            test_blob = b'x' * size
            lookup_hash = f'blob_test_{size}'
            
            conn.execute("""
                INSERT INTO client_side_urls (lookup_hash, encryption_salt, iv, encrypted_url) 
                VALUES (?, ?, ?, ?)
            """, (lookup_hash, test_blob, b'iv', b'url'))
            
            cursor = conn.execute("""
                SELECT encryption_salt FROM client_side_urls WHERE lookup_hash = ?
            """, (lookup_hash,))
            row = cursor.fetchone()
            assert len(row['encryption_salt']) == size
            assert row['encryption_salt'] == test_blob 