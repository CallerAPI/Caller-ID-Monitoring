import requests
from typing import Dict, Any

class CallerAPIService:
    BASE_URL = "https://callerapi.com/api"
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self.headers = {
            "X-Auth": self.api_key
        }
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account credits and status"""
        response = requests.get(
            f"{self.BASE_URL}/me",
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch account info: {response.text}")
        
        data = response.json()
        
        if data.get("status") != "success":
            raise ValueError(data.get("message", "API request failed"))
            
        return data
    
    def lookup_number(self, phone_number: str) -> Dict[str, Any]:
        """Lookup phone number information"""
        response = requests.get(
            f"{self.BASE_URL}/lookup/{phone_number}",
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code != 200:
            raise ValueError("Failed to lookup phone number")
        
        data = response.json()
        
        if not isinstance(data, dict) or data.get("status") != "success":
            raise ValueError(data.get("message", "API request failed"))
            
        return data
