"""
Etsy listing management
"""
from typing import List, Optional, Dict
from app.etsy.client import EtsyClient
from app.config import get_settings

settings = get_settings()


class ListingManager:
    """Manage Etsy listings"""
    
    def __init__(self, client: EtsyClient = None):
        self.client = client or EtsyClient()
        self.shop_id = settings.etsy_shop_id
        self.default_price = settings.etsy_default_price
        self.default_quantity = settings.etsy_default_quantity
    
    def create_listing(
        self,
        title: str,
        description: str,
        price: float = None,
        quantity: int = None,
        tags: List[str] = None,
        category_id: int = None
    ) -> Optional[int]:
        """
        Create a new Etsy listing
        
        Args:
            title: Listing title
            description: Listing description
            price: Price in USD
            quantity: Available quantity
            tags: List of tags
            category_id: Etsy category ID
            
        Returns:
            Listing ID or None
        """
        if not self.shop_id:
            print("Shop ID not configured")
            return None
        
        try:
            data = {
                'title': title,
                'description': description,
                'price': price or self.default_price,
                'quantity': quantity or self.default_quantity,
                'state': 'draft',  # Start as draft
                'who_made': 'i_did',
                'when_made': 'made_to_order',
                'is_supply': 'false',
                'taxonomy_id': category_id or 688,  # Default: Digital Items
            }
            
            if tags:
                data['tags'] = tags
            
            response = self.client.post(
                f'/application/shops/{self.shop_id}/listings',
                data=data
            )
            
            if response and 'listing_id' in response:
                return response['listing_id']
        
        except Exception as e:
            print(f"Error creating listing: {e}")
        
        return None
    
    def update_listing(
        self,
        listing_id: int,
        title: str = None,
        description: str = None,
        price: float = None,
        quantity: int = None
    ) -> bool:
        """
        Update an existing listing
        
        Args:
            listing_id: Listing ID
            title: New title
            description: New description
            price: New price
            quantity: New quantity
            
        Returns:
            True if successful
        """
        try:
            data = {}
            
            if title:
                data['title'] = title
            if description:
                data['description'] = description
            if price:
                data['price'] = price
            if quantity:
                data['quantity'] = quantity
            
            if not data:
                return True
            
            response = self.client.put(
                f'/application/shops/{self.shop_id}/listings/{listing_id}',
                data=data
            )
            
            return response is not None
        
        except Exception as e:
            print(f"Error updating listing: {e}")
            return False
    
    def activate_listing(self, listing_id: int) -> bool:
        """
        Activate a listing
        
        Args:
            listing_id: Listing ID
            
        Returns:
            True if successful
        """
        try:
            response = self.client.put(
                f'/application/shops/{self.shop_id}/listings/{listing_id}',
                data={'state': 'active'}
            )
            
            return response is not None
        
        except Exception as e:
            print(f"Error activating listing: {e}")
            return False
    
    def deactivate_listing(self, listing_id: int) -> bool:
        """
        Deactivate a listing
        
        Args:
            listing_id: Listing ID
            
        Returns:
            True if successful
        """
        try:
            response = self.client.put(
                f'/application/shops/{self.shop_id}/listings/{listing_id}',
                data={'state': 'inactive'}
            )
            
            return response is not None
        
        except Exception as e:
            print(f"Error deactivating listing: {e}")
            return False
    
    def delete_listing(self, listing_id: int) -> bool:
        """
        Delete a listing
        
        Args:
            listing_id: Listing ID
            
        Returns:
            True if successful
        """
        try:
            return self.client.delete(
                f'/application/shops/{self.shop_id}/listings/{listing_id}'
            )
        
        except Exception as e:
            print(f"Error deleting listing: {e}")
            return False
    
    def attach_image_to_listing(
        self,
        listing_id: int,
        image_id: int,
        is_primary: bool = False,
        rank: int = 0
    ) -> bool:
        """
        Attach an image to a listing
        
        Args:
            listing_id: Listing ID
            image_id: Image ID
            is_primary: Whether this is the primary image
            rank: Image rank/order
            
        Returns:
            True if successful
        """
        try:
            data = {
                'listing_image_id': image_id,
                'is_primary': is_primary,
                'rank': rank
            }
            
            response = self.client.post(
                f'/application/listings/{listing_id}/images',
                data=data
            )
            
            return response is not None
        
        except Exception as e:
            print(f"Error attaching image to listing: {e}")
            return False
    
    def upload_and_attach_images(
        self,
        listing_id: int,
        image_paths: List[str]
    ) -> List[int]:
        """
        Upload multiple images and attach to listing
        
        Args:
            listing_id: Listing ID
            image_paths: List of image file paths
            
        Returns:
            List of image IDs
        """
        image_ids = []
        
        for i, image_path in enumerate(image_paths):
            image_id = self.client.upload_listing_image(image_path)
            
            if image_id:
                image_ids.append(image_id)
                
                # Attach to listing
                self.attach_image_to_listing(
                    listing_id,
                    image_id,
                    is_primary=(i == 0),
                    rank=i
                )
        
        return image_ids
    
    def get_listing(self, listing_id: int) -> Optional[Dict]:
        """
        Get listing details
        
        Args:
            listing_id: Listing ID
            
        Returns:
            Listing data or None
        """
        try:
            return self.client.get(f'/application/listings/{listing_id}')
        except Exception as e:
            print(f"Error getting listing: {e}")
            return None
    
    def get_shop_listings(self, state: str = None) -> List[Dict]:
        """
        Get all listings for the shop
        
        Args:
            state: Filter by state (active, inactive, draft, etc.)
            
        Returns:
            List of listings
        """
        try:
            params = {}
            if state:
                params['state'] = state
            
            response = self.client.get(
                f'/application/shops/{self.shop_id}/listings',
                params=params
            )
            
            if response and 'results' in response:
                return response['results']
            
            return []
        
        except Exception as e:
            print(f"Error getting shop listings: {e}")
            return []
    
    def create_digital_listing(
        self,
        title: str,
        description: str,
        pdf_path: str,
        image_paths: List[str],
        price: float = None
    ) -> Optional[int]:
        """
        Create a complete digital listing with images and file
        
        Args:
            title: Listing title
            description: Listing description
            pdf_path: Path to PDF file
            image_paths: List of image paths
            price: Listing price
            
        Returns:
            Listing ID or None
        """
        # Create listing
        listing_id = self.create_listing(title, description, price)
        
        if not listing_id:
            return None
        
        # Upload and attach images
        self.upload_and_attach_images(listing_id, image_paths)
        
        # Upload digital file (may not be supported via API)
        file_id = self.client.upload_digital_file(listing_id, pdf_path)
        
        # Note: If file upload fails, user will need to manually upload
        # the PDF through Etsy dashboard
        if not file_id:
            print(
                "Warning: Digital file upload not supported via API. "
                "Please upload the PDF manually through Etsy dashboard."
            )
        
        return listing_id
    
    def generate_tags(self, metadata: Dict) -> List[str]:
        """
        Generate tags for listing based on metadata
        
        Args:
            metadata: PDF metadata
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add manufacturer as tag
        if metadata.get('manufacturer'):
            tags.append(metadata['manufacturer'].lower())
        
        # Add equipment type as tag
        if metadata.get('equipment_type'):
            tags.append(metadata['equipment_type'].lower())
        
        # Add model as tag
        if metadata.get('model'):
            tags.append(metadata['model'].lower())
        
        # Add year as tag
        if metadata.get('year'):
            tags.append(metadata['year'])
        
        # Add generic tags
        tags.extend([
            'digital download',
            'service manual',
            'repair manual',
            'instant download'
        ])
        
        # Ensure we don't exceed Etsy's tag limit (13 tags)
        return tags[:13]
