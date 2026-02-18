"""
Gumroad Platform Integration
Free digital download platform with API support
"""
import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from app.passive_income.platforms.base import BasePlatform, PlatformStatus, ListingResult


class GumroadPlatform(BasePlatform):
    """Gumroad platform integration for digital downloads"""
    
    name = "gumroad"
    display_name = "Gumroad"
    platform_type = "digital_download"
    supports_api_listing = True
    supports_digital_downloads = True
    is_free = True  # No upfront costs, takes percentage of sales
    
    # Gumroad limits
    max_title_length = 200
    max_description_length = 50000
    
    # Rate limiting (Gumroad doesn't publish limits, be conservative)
    rate_limit_requests = 500
    rate_limit_period = 3600
    
    # Required credentials
    required_credentials = ['api_token']
    
    def __init__(self, credentials: Dict = None, config: Dict = None):
        super().__init__(credentials, config)
        self.api_base = "https://api.gumroad.com/v2"
    
    def check_status(self) -> PlatformStatus:
        """Check Gumroad API connection status"""
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
                error=f"Missing API token"
            )
        
        try:
            # Test API by getting user info
            response = self._make_request('GET', '/user')
            
            if response.status_code == 200:
                data = response.json()
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
                    error="Invalid API token"
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
        """Create a new Gumroad product"""
        
        # Check credentials
        is_valid, missing = self.validate_credentials()
        if not is_valid:
            return self.requires_manual_action(
                'account_setup',
                "Gumroad API token required",
                {'missing_fields': missing}
            )
        
        # Prepare product data
        product_data = {
            'name': title[:self.max_title_length],
            'description': description[:self.max_description_length],
            'price': int(price * 100),  # Gumroad uses cents
            'currency': kwargs.get('currency', 'usd'),
            'publish': kwargs.get('publish', True),
            'max_purchase_count': kwargs.get('max_purchase_count', None),  # None = unlimited
        }
        
        # Add tags as custom permalink if provided
        if tags:
            # Gumroad uses custom permalink
            permalink = tags[0].lower().replace(' ', '-').replace('_', '-')
            if len(permalink) > 30:
                permalink = permalink[:30]
            product_data['custom_permalink'] = permalink
        
        try:
            # Create the product
            response = self._make_request(
                'POST',
                '/products',
                data=product_data
            )
            
            if response.status_code == 401:
                return self.requires_manual_action(
                    'authentication',
                    "Gumroad API token is invalid",
                    {}
                )
            
            if response.status_code not in [200, 201]:
                return ListingResult(
                    success=False,
                    error=f"Gumroad API error: {response.status_code} - {response.text}"
                )
            
            result = response.json()
            product = result.get('product', {})
            product_id = product.get('id')
            short_url = product.get('short_url')
            
            # Upload file if provided
            if file_path and product_id:
                file_result = self._upload_file(product_id, file_path)
                if not file_result['success']:
                    return ListingResult(
                        success=True,
                        listing_id=product_id,
                        listing_url=short_url,
                        error=f"Product created but file upload failed: {file_result.get('error')}"
                    )
            
            # Upload thumbnail if provided
            if images and product_id:
                self._upload_thumbnail(product_id, images[0])
            
            return ListingResult(
                success=True,
                listing_id=product_id,
                listing_url=short_url or f"https://gum.co/{product.get('custom_permalink', product_id)}"
            )
            
        except Exception as e:
            return ListingResult(
                success=False,
                error=f"Error creating product: {str(e)}"
            )
    
    def update_listing(
        self,
        listing_id: str,
        title: str = None,
        description: str = None,
        price: float = None,
        **kwargs
    ) -> ListingResult:
        """Update an existing Gumroad product"""
        
        update_data = {}
        if title:
            update_data['name'] = title[:self.max_title_length]
        if description:
            update_data['description'] = description[:self.max_description_length]
        if price is not None:
            update_data['price'] = int(price * 100)  # Cents
        
        try:
            response = self._make_request(
                'PUT',
                f'/products/{listing_id}',
                data=update_data
            )
            
            if response.status_code == 200:
                result = response.json()
                product = result.get('product', {})
                return ListingResult(
                    success=True,
                    listing_id=listing_id,
                    listing_url=product.get('short_url')
                )
            else:
                return ListingResult(
                    success=False,
                    error=f"Update failed: {response.status_code}"
                )
                
        except Exception as e:
            return ListingResult(success=False, error=str(e))
    
    def delete_listing(self, listing_id: str) -> ListingResult:
        """Delete a Gumroad product"""
        try:
            response = self._make_request(
                'DELETE',
                f'/products/{listing_id}'
            )
            
            if response.status_code == 200:
                return ListingResult(success=True, listing_id=listing_id)
            else:
                return ListingResult(
                    success=False,
                    error=f"Delete failed: {response.status_code}"
                )
                
        except Exception as e:
            return ListingResult(success=False, error=str(e))
    
    def get_listing(self, listing_id: str) -> Dict:
        """Get Gumroad product details"""
        try:
            response = self._make_request(
                'GET',
                f'/products/{listing_id}'
            )
            
            if response.status_code == 200:
                return response.json().get('product', {})
            return {'error': f"Failed to get product: {response.status_code}"}
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_sales(self, days: int = 30) -> List[Dict]:
        """Get Gumroad sales data"""
        from datetime import timedelta
        
        sales = []
        start_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            # Get all sales
            response = self._make_request(
                'GET',
                '/sales',
                params={'after': start_date.strftime('%Y-%m-%d')}
            )
            
            if response.status_code == 200:
                data = response.json()
                for sale in data.get('sales', []):
                    sales.append({
                        'transaction_id': sale.get('id'),
                        'listing_id': sale.get('product_id'),
                        'product_name': sale.get('product_name'),
                        'amount': float(sale.get('price', 0)) / 100,
                        'quantity': sale.get('quantity', 1),
                        'date': sale.get('created_at'),
                        'email': sale.get('email'),
                        'fee': float(sale.get('fee', 0)) / 100
                    })
            
            return sales
            
        except Exception as e:
            print(f"Error fetching Gumroad sales: {e}")
            return []
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an authenticated request to Gumroad API"""
        url = f"{self.api_base}{endpoint}"
        
        # Gumroad uses token as form data or query param
        if 'data' in kwargs:
            kwargs['data']['access_token'] = self.credentials.get('api_token')
        elif 'params' in kwargs:
            kwargs['params']['access_token'] = self.credentials.get('api_token')
        else:
            kwargs['data'] = {'access_token': self.credentials.get('api_token')}
        
        self._check_rate_limit()
        self._record_request()
        
        return requests.request(method, url, **kwargs)
    
    def _upload_file(self, product_id: str, file_path: str) -> Dict:
        """Upload a file to a product"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = self._make_request(
                    'POST',
                    f'/products/{product_id}/file',
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
    
    def _upload_thumbnail(self, product_id: str, image_path: str) -> bool:
        """Upload a thumbnail image"""
        try:
            with open(image_path, 'rb') as f:
                files = {'thumbnail': f}
                response = self._make_request(
                    'PUT',
                    f'/products/{product_id}',
                    files=files
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Error uploading thumbnail: {e}")
            return False
    
    def generate_seo_title(self, base_title: str, metadata: Dict = None) -> str:
        """Generate Gumroad-optimized title"""
        title = base_title
        
        # Gumroad titles can be longer
        if 'manual' in title.lower() and 'pdf' not in title.lower():
            title += ' [PDF]'
        
        if len(title) > self.max_title_length:
            title = title[:self.max_title_length - 3] + '...'
        
        return title
