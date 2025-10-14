"""
OCI REST API Client - Optimized for minimal token usage
Based on Oracle's Postman collection patterns
"""

import base64
import hashlib
import json
import os
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import requests


class OCIRestClient:
    """Optimized OCI REST API client using .oci/config file"""
    
    def __init__(self, profile: str = "DEFAULT", region: str = None):
        self.profile = profile
        self.region = region or self._get_default_region()
        self.config = self._load_oci_config()
        self.base_url = f"https://{self._get_service_endpoint()}"
        
    def _load_oci_config(self) -> dict[str, str]:
        """Load OCI configuration from ~/.oci/config file"""
        config_path = os.path.expanduser("~/.oci/config")
        if not os.path.exists(config_path):
            raise RuntimeError("OCI config file not found at ~/.oci/config")
            
        config = {}
        current_profile = None
        
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_profile = line[1:-1]
                elif '=' in line and current_profile == self.profile:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
                    
        required_keys = ['tenancy', 'user', 'fingerprint', 'key_file']
        missing = [k for k in required_keys if k not in config]
        if missing:
            raise RuntimeError(f"Missing required config keys: {missing}")
            
        # Load private key
        key_path = os.path.expanduser(config['key_file'])
        with open(key_path) as f:
            config['private_key'] = f.read()
            
        return config
    
    def _get_default_region(self) -> str:
        """Get default region from config or environment"""
        return os.environ.get('OCI_REGION', 'us-ashburn-1')
    
    def _get_service_endpoint(self) -> str:
        """Get service endpoint based on region"""
        region_map = {
            'us-ashburn-1': 'iaas.us-ashburn.oraclecloud.com',
            'us-phoenix-1': 'iaas.us-phoenix.oraclecloud.com',
            'eu-frankfurt-1': 'iaas.eu-frankfurt.oraclecloud.com',
            'uk-london-1': 'iaas.uk-london.oraclecloud.com',
            'ap-sydney-1': 'iaas.ap-sydney.oraclecloud.com',
        }
        return region_map.get(self.region, f"iaas.{self.region}.oraclecloud.com")
    
    def _sign_request(self, method: str, url: str, headers: dict[str, str], body: str = None) -> dict[str, str]:
        """Sign request using OCI signature algorithm"""
        # Parse URL
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
            
        # Create signing string
        signing_string = f"{method}\n{headers.get('host', '')}\n{path}\n{headers.get('date', '')}\n{headers.get('content-type', '')}\n{headers.get('x-content-sha256', '')}"
        
        # Sign with private key (simplified for now)
        # TODO: Implement proper OCI signature algorithm
        signature_b64 = base64.b64encode(signing_string.encode()).decode()
        
        # Create authorization header
        auth_string = f"Signature version=\"1\",keyId=\"{self.config['tenancy']}/{self.config['user']}/{self.config['fingerprint']}\",algorithm=\"rsa-sha256\",headers=\"date host (request-target)\",signature=\"{signature_b64}\""
        
        return {
            'Authorization': auth_string,
            'opc-request-id': f"mcp-oci-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
    
    def request(self, method: str, path: str, params: dict[str, Any] = None, 
                data: dict[str, Any] = None, headers: dict[str, str] = None) -> dict[str, Any]:
        """Make authenticated OCI REST API request"""
        url = f"{self.base_url}{path}"
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json',
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Host': urlparse(url).netloc,
            **(headers or {})
        }
        
        # Prepare body
        body = json.dumps(data) if data else None
        if body:
            body_hash = hashlib.sha256(body.encode()).digest()
            request_headers['x-content-sha256'] = base64.b64encode(body_hash).decode()
        
        # Sign request
        auth_headers = self._sign_request(method, url, request_headers, body)
        request_headers.update(auth_headers)
        
        # Make request
        response = requests.request(
            method=method,
            url=url,
            params=params,
            data=body,
            headers=request_headers,
            timeout=30
        )
        
        # Parse response
        try:
            result = response.json()
        except:
            result = {"error": "Invalid JSON response", "status_code": response.status_code}
            
        # Add status info
        result["_status"] = {
            "code": response.status_code,
            "ok": response.ok
        }
        
        return result
    
    def get(self, path: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """Make GET request"""
        return self.request("GET", path, params=params)
    
    def post(self, path: str, data: dict[str, Any] = None) -> dict[str, Any]:
        """Make POST request"""
        return self.request("POST", path, data=data)
    
    def put(self, path: str, data: dict[str, Any] = None) -> dict[str, Any]:
        """Make PUT request"""
        return self.request("PUT", path, data=data)
    
    def delete(self, path: str) -> dict[str, Any]:
        """Make DELETE request"""
        return self.request("DELETE", path)


def create_client(profile: str = "DEFAULT", region: str = None) -> OCIRestClient:
    """Create OCI REST client instance"""
    return OCIRestClient(profile=profile, region=region)
