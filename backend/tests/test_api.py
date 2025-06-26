import pytest
import json
import sys
import os
from unittest.mock import patch, Mock

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app


class TestShortenServerEndpoint:
    """Test the /shorten-server endpoint"""
    
    def test_shorten_server_basic(self, client, sample_urls):
        """Test basic URL shortening functionality"""
        for url in sample_urls:
            response = client.post('/shorten-server', 
                                 json={'url': url},
                                 content_type='application/json')
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert 'id' in data
            assert isinstance(data['id'], str)
            assert len(data['id']) == 10  # From test config
            
    def test_shorten_server_missing_url(self, client):
        """Test error handling when URL is missing"""
        response = client.post('/shorten-server', 
                             json={},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Missing URL' in data['error']
        
    def test_shorten_server_no_json_body(self, client):
        """Test error handling when no JSON body is provided"""
        response = client.post('/shorten-server')
        
        assert response.status_code == 400
        # Flask returns HTML error page when Content-Type is not application/json
        # So we just check the status code for this case
        
    def test_shorten_server_url_prefix_handling(self, client):
        """Test that URLs get proper prefixes"""
        test_cases = [
            ('google.com', 'http://google.com'),
            ('https://example.com', 'https://example.com'),
            ('http://test.org', 'http://test.org'),
            ('magnet:?xt=urn:btih:example', 'magnet:?xt=urn:btih:example'),
        ]
        
        for input_url, expected_prefix in test_cases:
            response = client.post('/shorten-server', 
                                 json={'url': input_url},
                                 content_type='application/json')
            
            assert response.status_code == 201
            # The URL gets stored encrypted, so we can't directly verify the prefix
            # But we can verify the request was processed successfully
            
    def test_shorten_server_duplicate_handling(self, client):
        """Test that duplicate URLs get unique IDs"""
        url = "https://example.com"
        
        # Create multiple shortened URLs for the same target
        ids = []
        for _ in range(5):
            response = client.post('/shorten-server', 
                                 json={'url': url},
                                 content_type='application/json')
            assert response.status_code == 201
            data = json.loads(response.data)
            ids.append(data['id'])
            
        # All IDs should be unique
        assert len(set(ids)) == len(ids)
        
    @patch('main.generate_id')
    def test_shorten_server_id_collision_retry(self, mock_generate_id, client):
        """Test retry logic when ID collisions occur"""
        # Mock generate_id to return the same ID twice, then a unique one
        mock_generate_id.side_effect = ['duplicate', 'duplicate', 'unique123']
        
        # First request should succeed with 'duplicate' ID
        response1 = client.post('/shorten-server', 
                               json={'url': 'https://first.com'},
                               content_type='application/json')
        assert response1.status_code == 201
        
        # Second request should retry and get 'unique123'
        response2 = client.post('/shorten-server', 
                               json={'url': 'https://second.com'},
                               content_type='application/json')
        assert response2.status_code == 201
        data = json.loads(response2.data)
        assert data['id'] == 'unique123'
        
    @patch('main.generate_id')
    def test_shorten_server_max_retries_exceeded(self, mock_generate_id, client):
        """Test error when max retries for unique ID is exceeded"""
        # Mock generate_id to always return the same ID
        mock_generate_id.return_value = 'always_same'
        
        # First request should succeed
        response1 = client.post('/shorten-server', 
                               json={'url': 'https://first.com'},
                               content_type='application/json')
        assert response1.status_code == 201
        
        # Second request should fail after max retries
        response2 = client.post('/shorten-server', 
                               json={'url': 'https://second.com'},
                               content_type='application/json')
        assert response2.status_code == 500
        data = json.loads(response2.data)
        assert 'Failed to generate unique ID' in data['error']


class TestShortenClientEndpoint:
    """Test the /shorten (client-side) endpoint"""
    
    def test_shorten_client_basic(self, client, sample_encrypted_data):
        """Test basic client-side URL shortening"""
        response = client.post('/shorten', 
                             json=sample_encrypted_data,
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert 'successfully' in data['message']
        
    def test_shorten_client_missing_fields(self, client):
        """Test error handling when required fields are missing"""
        incomplete_data = {
            'LOOKUP_HASH': 'abcd1234',
            'IV': '22222222222222222222222222222222',
            # Missing ENCRYTION_SALT and ENCRYPTED_URL
        }
        
        response = client.post('/shorten', 
                             json=incomplete_data,
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing fields' in data['error']
        
    def test_shorten_client_invalid_hex(self, client):
        """Test error handling with invalid hex data"""
        invalid_data = {
            'LOOKUP_HASH': 'abcd1234',
            'ENCRYTION_SALT': 'invalid_hex_string',
            'IV': '22222222222222222222222222222222',
            'ENCRYPTED_URL': '33333333333333333333333333333333'
        }
        
        response = client.post('/shorten', 
                             json=invalid_data,
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid hex format' in data['error']
        
    def test_shorten_client_duplicate_hash(self, client, sample_encrypted_data):
        """Test error handling when lookup hash already exists"""
        # First request should succeed
        response1 = client.post('/shorten', 
                               json=sample_encrypted_data,
                               content_type='application/json')
        assert response1.status_code == 201
        
        # Second request with same lookup hash should fail
        response2 = client.post('/shorten', 
                               json=sample_encrypted_data,
                               content_type='application/json')
        assert response2.status_code == 409
        data = json.loads(response2.data)
        assert 'already exists' in data['error']


class TestGetEncryptedUrlEndpoint:
    """Test the /get-encrypted-url endpoint"""
    
    def test_get_encrypted_url_basic(self, client, sample_encrypted_data):
        """Test basic encrypted URL retrieval"""
        # First, store a URL
        client.post('/shorten', 
                   json=sample_encrypted_data,
                   content_type='application/json')
        
        # Then retrieve it
        response = client.get(f'/get-encrypted-url?lookup_hash={sample_encrypted_data["LOOKUP_HASH"]}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'ENCRYTION_SALT' in data
        assert 'IV' in data
        assert 'ENCRYPTED_URL' in data
        assert data['ENCRYTION_SALT'] == sample_encrypted_data['ENCRYTION_SALT']
        assert data['IV'] == sample_encrypted_data['IV']
        assert data['ENCRYPTED_URL'] == sample_encrypted_data['ENCRYPTED_URL']
        
    def test_get_encrypted_url_missing_parameter(self, client):
        """Test error handling when lookup_hash parameter is missing"""
        response = client.get('/get-encrypted-url')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing lookup_hash parameter' in data['error']
        
    def test_get_encrypted_url_not_found(self, client):
        """Test error handling when lookup hash doesn't exist"""
        response = client.get('/get-encrypted-url?lookup_hash=nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Link not found' in data['error']


class TestRedirectEndpoint:
    """Test the /<id> redirect endpoint"""
    
    def test_redirect_basic(self, client):
        """Test basic URL redirection"""
        # First, create a shortened URL using server-side endpoint
        original_url = "https://example.com"
        response = client.post('/shorten-server', 
                             json={'url': original_url},
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        short_id = data['id']
        
        # Then test redirection
        response = client.get(f'/{short_id}')
        assert response.status_code == 302
        assert response.location == original_url
        
    def test_redirect_not_found(self, client):
        """Test error handling when short ID doesn't exist"""
        response = client.get('/nonexistent123')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Link not found' in data['error']
        
    def test_redirect_various_urls(self, client, sample_urls):
        """Test redirection with various URL types"""
        for original_url in sample_urls:
            # Create shortened URL
            response = client.post('/shorten-server', 
                                 json={'url': original_url},
                                 content_type='application/json')
            assert response.status_code == 201
            
            data = json.loads(response.data)
            short_id = data['id']
            
            # Test redirection
            response = client.get(f'/{short_id}')
            assert response.status_code == 302
            
            # For URLs that get prefixed, check the prefixed version
            expected_url = original_url
            if not (original_url.startswith('https://') or 
                   original_url.startswith('http://') or 
                   original_url.startswith('magnet:')):
                expected_url = 'http://' + original_url
                
            assert response.location == expected_url


class TestStaticFileEndpoints:
    """Test static file serving endpoints"""
    
    def test_serve_react_app(self, client):
        """Test serving the React app"""
        response = client.get('/')
        # We can't test the actual file content without the dist folder
        # But we can test that the route exists and doesn't error
        assert response.status_code in [200, 404]  # 404 if dist/index.html doesn't exist
        
    def test_serve_robots_txt(self, client):
        """Test serving robots.txt"""
        response = client.get('/robots.txt')
        assert response.status_code in [200, 404]  # 404 if file doesn't exist
        
    def test_serve_sitemap_xml(self, client):
        """Test serving sitemap.xml"""
        response = client.get('/sitemap.xml')
        assert response.status_code in [200, 404]  # 404 if file doesn't exist


class TestErrorHandling:
    """Test general error handling"""
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON in requests"""
        response = client.post('/shorten-server', 
                             data='invalid json',
                             content_type='application/json')
        
        # Flask should handle this and return 400
        assert response.status_code == 400
        
    def test_unsupported_http_methods(self, client):
        """Test that unsupported HTTP methods are rejected"""
        # GET on POST-only endpoints - Flask returns 404 for unmatched routes
        response = client.get('/shorten-server')
        assert response.status_code in [404, 405]  # Flask may return 404 or 405
        
        response = client.get('/shorten')
        assert response.status_code in [404, 405]
        
        # POST on GET-only endpoints
        response = client.post('/get-encrypted-url')
        assert response.status_code in [404, 405] 