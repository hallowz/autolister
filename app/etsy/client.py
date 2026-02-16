"""
Etsy API client for authentication and API calls
"""
import requests
from typing import Dict, Optional
from app.config import get_settings

settings = get_settings()


class EtsyClient:
    """Etsy API client with OAuth authentication"""
    
    # Etsy API endpoints
    BASE_URL = "https://openapi.etsy.com/v3"
    OAUTH_URL = "https://openapi.etsy.com/v3/oauth"
    
    def __init__(self):
        self.api_key = settings.etsy_api_key
        self.api_secret = settings.etsy_api_secret
        self.access_token = settings.etsy_access_token
        self.access_token_secret = settings.etsy_access_token_secret
        self.shop_id = settings.etsy_shop_id
        
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup session with authentication headers"""
        if self.access_token:
            self.session.headers.update({
                'x-api-key': self.api_key,
                'Authorization': f'Bearer {self.access_token}'
            })
        else:
            self.session.headers.update({
                'x-api-key': self.api_key
            })
    
    def get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make GET request to Etsy API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response JSON or None
        """
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Etsy API GET error: {e}")
            return None
    
    def post(self, endpoint: str, data: Dict = None, files: Dict = None) -> Optional[Dict]:
        """
        Make POST request to Etsy API
        
        Args:
            endpoint: API endpoint
            data: Request data
            files: Files to upload
            
        Returns:
            Response JSON or None
        """
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.post(url, json=data, files=files)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Etsy API POST error: {e}")
            return None
    
    def put(self, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """
        Make PUT request to Etsy API
        
        Args:
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Response JSON or None
        """
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.put(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Etsy API PUT error: {e}")
            return None
    
    def delete(self, endpoint: str) -> bool:
        """
        Make DELETE request to Etsy API
        
        Args:
            endpoint: API endpoint
            
        Returns:
            True if successful
        """
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.delete(url)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Etsy API DELETE error: {e}")
            return False
    
    def get_shop_info(self) -> Optional[Dict]:
        """
        Get shop information
        
        Returns:
            Shop info or None
        """
        if not self.shop_id:
            return None
        
        return self.get(f"/application/shops/{self.shop_id}")
    
    def upload_listing_image(self, image_path: str) -> Optional[int]:
        """
        Upload an image for a listing
        
        Args:
            image_path: Path to image file
            
        Returns:
            Image ID or None
        """
        try:
            with open(image_path, 'rb') as f:
                files = {
                    'image': f
                }
                response = self.post('/application/listings/images', files=files)
                
                if response and 'listing_image_id' in response:
                    return response['listing_image_id']
        
        except Exception as e:
            print(f"Error uploading image: {e}")
        
        return None
    
    def upload_digital_file(self, listing_id: int, file_path: str) -> Optional[int]:
        """
        Upload a digital file for a listing
        
        Args:
            listing_id: Listing ID
            file_path: Path to file
            
        Returns:
            File ID or None
        
        Note: This endpoint may not be available in Etsy's Open API.
        Digital files may need to be uploaded manually through the Etsy dashboard.
        """
        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': f
                }
                data = {
                    'listing_id': listing_id
                }
                response = self.post(
                    f'/application/listings/{listing_id}/files',
                    data=data,
                    files=files
                )
                
                if response and 'listing_file_id' in response:
                    return response['listing_file_id']
        
        except Exception as e:
            print(f"Error uploading digital file: {e}")
        
        return None
    
    def test_connection(self) -> bool:
        """
        Test API connection
        
        Returns:
            True if connection successful
        """
        response = self.get('/application/users/me')
        return response is not None
