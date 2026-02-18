"""
Etsy Platform Integration
"""
import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from app.passive_income.platforms.base import BasePlatform, PlatformStatus, ListingResult


class EtsyPlatform(BasePlatform):
    """Etsy platform integration for digital downloads"""
    
    name = "etsy"
    display_name = "Etsy"
    platform_type = "digital_download"
    supports_api_listing = True
    supports_digital_downloads = True
    is_free = True
    
    # Etsy-specific limits
    max_title_length = 140
    max_tags = 13
    max_tag_length = 20
    max_description_length = 13000
    
    # Rate limiting (Etsy: 10 requests per second, 10000 per day)
    rate_limit_requests = 10000
    rate_limit_period = 86400
    
    # Required credentials
    required_credentials = ['api_key', 'api_secret', 'access_token', 'shop_id']
    
    def __init__(self, credentials: Dict = None, config: Dict = None):
        super().__init__(credentials, config)
        self.api_base = "https://openapi.etsy.com/v3"
        self._shop_id = credentials.get('shop_id') if credentials else None
    
    def check_status(self) -> PlatformStatus:
        """Check Etsy API connection status"""
        if not self.credentials:
            return PlatformStatus(
                is_configured=False,
                requires_auth=True,
                error="No credentials provided"
            )
        
        is_valid, missing = self.validate_credentials()
        if not is_valid:
            return PlatformStatus(
                is_configured=False,
                requires_auth=True,
                error=f"Missing credentials: {', '.join(missing)}"
            )
        
        try:
            # Test API connection by getting shop info
            response = self._make_request('GET', f'/shops/{self._shop_id}')
            
            if response.status_code == 200:
                return PlatformStatus(
                    is_configured=True,
                    is_connected=True,
                    requires_auth=False
                )
            elif response.status_code == 401:
                return PlatformStatus(
                    is_configured=True,
                    is_connected=False,
                    requires_auth=True,
                    error="Authentication expired"
                )
            else:
                return PlatformStatus(
                    is_configured=True,
                    is_connected=False,
                    error=f"API error: {response.status_code}"
                )
                
        except Exception as e:
            return PlatformStatus(
                is_configured=True,
                is_connected=False,
                error=str(e)
            )
    
    def create_listing(
        self,
        title: str,
        description: str,
        price: float,
        file_path: str = None,
        images: List[str] = None,
        tags: List[str] = None,
        **kwargs
    ) -> ListingResult:
        """Create a new Etsy listing"""
        
        # Check credentials first
        is_valid, missing = self.validate_credentials()
        if not is_valid:
            return self.requires_manual_action(
                'account_setup',
                f"Etsy credentials missing: {', '.join(missing)}",
                {'missing_fields': missing}
            )
        
        # Prepare listing data
        listing_data = {
            'shop_id': self._shop_id,
            'title': self.generate_seo_title(title),
            'description': description[:self.max_description_length],
            'price': price,
            'quantity': kwargs.get('quantity', 999),
            'is_digital': True,
            'file_data': None,  # Will be uploaded separately
            'taxonomy_id': kwargs.get('taxonomy_id', 1460),  # Digital items
            'who_made': 'i_did',
            'when_made': 'made_to_order',
            'shipping_profile_id': None,  # Digital doesn't need shipping
        }
        
        # Add tags
        if tags:
            listing_data['tags'] = self.generate_tags(tags)
        
        try:
            # Create the listing
            response = self._make_request(
                'POST',
                f'/shops/{self._shop_id}/listings',
                json=listing_data
            )
            
            if response.status_code == 401:
                return self.requires_manual_action(
                    'authentication',
                    "Etsy authentication expired. Please re-authenticate.",
                    {'auth_url': self._get_auth_url()}
                )
            
            if response.status_code == 403:
                return self.requires_manual_action(
                    'verification',
                    "Etsy account needs verification or permission upgrade.",
                    {'reason': response.text}
                )
            
            if response.status_code not in [200, 201]:
                return ListingResult(
                    success=False,
                    error=f"Etsy API error: {response.status_code} - {response.text}"
                )
            
            result = response.json()
            listing_id = result.get('listing_id')
            
            # Upload images if provided
            if images and listing_id:
                self._upload_images(listing_id, images)
            
            # Upload digital file if provided
            if file_path and listing_id:
                file_result = self._upload_digital_file(listing_id, file_path)
                if not file_result['success']:
                    return ListingResult(
                        success=True,
                        listing_id=str(listing_id),
                        listing_url=f"https://etsy.com/listing/{listing_id}",
                        error=f"Listing created but file upload failed: {file_result.get('error')}"
                    )
            
            return ListingResult(
                success=True,
                listing_id=str(listing_id),
                listing_url=f"https://etsy.com/listing/{listing_id}"
            )
            
        except Exception as e:
            return ListingResult(
                success=False,
                error=f"Error creating listing: {str(e)}"
            )
    
    def update_listing(
        self,
        listing_id: str,
        title: str = None,
        description: str = None,
        price: float = None,
        **kwargs
    ) -> ListingResult:
        """Update an existing Etsy listing"""
        
        update_data = {}
        if title:
            update_data['title'] = self.generate_seo_title(title)
        if description:
            update_data['description'] = description[:self.max_description_length]
        if price is not None:
            update_data['price'] = price
        
        try:
            response = self._make_request(
                'PUT',
                f'/shops/{self._shop_id}/listings/{listing_id}',
                json=update_data
            )
            
            if response.status_code == 200:
                return ListingResult(
                    success=True,
                    listing_id=listing_id,
                    listing_url=f"https://etsy.com/listing/{listing_id}"
                )
            else:
                return ListingResult(
                    success=False,
                    error=f"Update failed: {response.status_code}"
                )
                
        except Exception as e:
            return ListingResult(success=False, error=str(e))
    
    def delete_listing(self, listing_id: str) -> ListingResult:
        """Delete/remove an Etsy listing"""
        try:
            response = self._make_request(
                'DELETE',
                f'/shops/{self._shop_id}/listings/{listing_id}'
            )
            
            if response.status_code == 204:
                return ListingResult(success=True, listing_id=listing_id)
            else:
                return ListingResult(
                    success=False,
                    error=f"Delete failed: {response.status_code}"
                )
                
        except Exception as e:
            return ListingResult(success=False, error=str(e))
    
    def get_listing(self, listing_id: str) -> Dict:
        """Get Etsy listing details"""
        try:
            response = self._make_request(
                'GET',
                f'/listings/{listing_id}'
            )
            
            if response.status_code == 200:
                return response.json()
            return {'error': f"Failed to get listing: {response.status_code}"}
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_sales(self, days: int = 30) -> List[Dict]:
        """Get Etsy sales/revenue data"""
        from datetime import timedelta
        
        sales = []
        start_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            # Get transactions from orders
            response = self._make_request(
                'GET',
                f'/shops/{self._shop_id}/transactions',
                params={'was_paid': True}
            )
            
            if response.status_code == 200:
                data = response.json()
                for tx in data.get('results', []):
                    tx_date = datetime.fromisoformat(tx.get('create_date', '').replace('Z', ''))
                    if tx_date >= start_date:
                        sales.append({
                            'transaction_id': tx.get('transaction_id'),
                            'listing_id': tx.get('listing_id'),
                            'amount': float(tx.get('price', 0)),
                            'quantity': tx.get('quantity', 1),
                            'date': tx.get('create_date'),
                            'buyer_id': tx.get('buyer_user_id')
                        })
            
            return sales
            
        except Exception as e:
            print(f"Error fetching Etsy sales: {e}")
            return []
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an authenticated request to Etsy API"""
        url = f"{self.api_base}{endpoint}"
        
        headers = {
            'Authorization': f"Bearer {self.credentials.get('access_token')}",
            'x-api-key': self.credentials.get('api_key'),
            'Content-Type': 'application/json'
        }
        
        self._check_rate_limit()
        self._record_request()
        
        return requests.request(method, url, headers=headers, **kwargs)
    
    def _upload_images(self, listing_id: int, images: List[str]) -> bool:
        """Upload images to a listing"""
        for i, image_path in enumerate(images[:5]):  # Max 5 images
            try:
                with open(image_path, 'rb') as f:
                    files = {'image': f}
                    response = self._make_request(
                        'POST',
                        f'/shops/{self._shop_id}/listings/{listing_id}/images',
                        files=files
                    )
                    if response.status_code not in [200, 201]:
                        print(f"Failed to upload image {i+1}: {response.status_code}")
            except Exception as e:
                print(f"Error uploading image {i+1}: {e}")
        return True
    
    def _upload_digital_file(self, listing_id: int, file_path: str) -> Dict:
        """Upload a digital file to a listing"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = self._make_request(
                    'POST',
                    f'/shops/{self._shop_id}/listings/{listing_id}/files',
                    files=files
                )
                
                if response.status_code in [200, 201]:
                    return {'success': True}
                return {
                    'success': False,
                    'error': f"Upload failed: {response.status_code}"
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_auth_url(self) -> str:
        """Get OAuth authorization URL"""
        # This would be implemented for OAuth flow
        return "https://www.etsy.com/oauth/connect"
    
    def generate_seo_title(self, base_title: str, metadata: Dict = None) -> str:
        """Generate Etsy-optimized title"""
        title = base_title
        
        # Add digital download suffix if not present
        if 'digital' not in title.lower():
            title += ' | Digital Download'
        
        # Add PDF if not present and it's a PDF
        if metadata and metadata.get('file_type') == 'pdf' and 'pdf' not in title.lower():
            if len(title) < self.max_title_length - 5:
                title += ' PDF'
        
        # Truncate to Etsy limit
        if len(title) > self.max_title_length:
            title = title[:self.max_title_length - 3] + '...'
        
        return title
