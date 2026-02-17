#!/usr/bin/env python3
"""
Test script to verify the /pending API endpoint
Run this on the Raspberry Pi to test the API
"""
import requests
import json
from app.config import get_settings

def test_pending_api():
    """Test the /pending API endpoint"""
    settings = get_settings()
    url = f"http://{settings.dashboard_host}:{settings.dashboard_port}/api/pending"
    
    print(f"Testing API endpoint: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if isinstance(data, list):
                print(f"\nTotal pending manuals returned: {len(data)}")
            elif isinstance(data, dict) and 'manuals' in data:
                print(f"\nTotal pending manuals returned: {len(data['manuals'])}")
        else:
            print(f"Error response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Connection Error: Could not connect to the API endpoint")
        print("Make sure the application is running on the Raspberry Pi")
    except requests.exceptions.Timeout:
        print("Timeout: The request timed out")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pending_api()
