"""
Processing queue manager for managing manual processing queue
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import Manual


class ProcessingQueueManager:
    """Manages the processing queue for manuals"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_to_queue(self, manual_id: int) -> int:
        """
        Add a manual to the processing queue
        
        Args:
            manual_id: ID of the manual to add to queue
            
        Returns:
            Queue position assigned to the manual
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual:
            raise ValueError(f"Manual with ID {manual_id} not found")
        
        # Get the current highest queue position
        highest_position = self.db.query(Manual.queue_position).filter(
            Manual.queue_position.isnot(None)
        ).order_by(Manual.queue_position.desc()).first()
        
        next_position = (highest_position[0] + 1) if highest_position else 1
        
        manual.queue_position = next_position
        manual.processing_state = 'queued'
        manual.status = 'downloaded'  # Update status to show it's in queue
        self.db.commit()
        
        return next_position
    
    def remove_from_queue(self, manual_id: int) -> None:
        """
        Remove a manual from the processing queue and reposition remaining items
        
        Args:
            manual_id: ID of the manual to remove from queue
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual:
            raise ValueError(f"Manual with ID {manual_id} not found")
        
        removed_position = manual.queue_position
        
        # Clear queue position and processing state
        manual.queue_position = None
        manual.processing_state = None
        manual.processing_started_at = None
        manual.processing_completed_at = None
        self.db.commit()
        
        # Reposition all items after the removed one
        if removed_position:
            self._reposition_after(removed_position)
    
    def get_queue(self) -> List[Manual]:
        """
        Get all manuals currently in the processing queue, ordered by position
        
        Returns:
            List of manuals in queue order
        """
        return self.db.query(Manual).filter(
            Manual.queue_position.isnot(None)
        ).order_by(Manual.queue_position).all()
    
    def get_queue_position(self, manual_id: int) -> Optional[int]:
        """
        Get the queue position of a manual
        
        Args:
            manual_id: ID of the manual
            
        Returns:
            Queue position or None if not in queue
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        return manual.queue_position if manual else None
    
    def move_in_queue(self, manual_id: int, new_position: int) -> None:
        """
        Move a manual to a new position in the queue
        
        Args:
            manual_id: ID of the manual to move
            new_position: New queue position (1-based)
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual:
            raise ValueError(f"Manual with ID {manual_id} not found")
        
        if manual.queue_position is None:
            raise ValueError(f"Manual {manual_id} is not in the queue")
        
        old_position = manual.queue_position
        if old_position == new_position:
            return
        
        # Get all manuals in queue
        queue = self.get_queue()
        max_position = len(queue)
        
        if new_position < 1 or new_position > max_position:
            raise ValueError(f"New position must be between 1 and {max_position}")
        
        # Shift positions
        if new_position < old_position:
            # Moving up: shift items between new_position and old_position-1 down
            self.db.query(Manual).filter(
                Manual.queue_position >= new_position,
                Manual.queue_position < old_position,
                Manual.id != manual_id
            ).update({
                'queue_position': Manual.queue_position + 1
            })
        else:
            # Moving down: shift items between old_position+1 and new_position up
            self.db.query(Manual).filter(
                Manual.queue_position > old_position,
                Manual.queue_position <= new_position,
                Manual.id != manual_id
            ).update({
                'queue_position': Manual.queue_position - 1
            })
        
        # Update the moved manual's position
        manual.queue_position = new_position
        self.db.commit()
    
    def move_up(self, manual_id: int) -> None:
        """
        Move a manual one position up in the queue
        
        Args:
            manual_id: ID of the manual to move
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual or manual.queue_position is None:
            raise ValueError(f"Manual {manual_id} is not in the queue")
        
        if manual.queue_position > 1:
            self.move_in_queue(manual_id, manual.queue_position - 1)
    
    def move_down(self, manual_id: int) -> None:
        """
        Move a manual one position down in the queue
        
        Args:
            manual_id: ID of the manual to move
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual or manual.queue_position is None:
            raise ValueError(f"Manual {manual_id} is not in the queue")
        
        queue = self.get_queue()
        max_position = len(queue)
        
        if manual.queue_position < max_position:
            self.move_in_queue(manual_id, manual.queue_position + 1)
    
    def set_processing_state(self, manual_id: int, state: str) -> None:
        """
        Set the processing state of a manual
        
        Args:
            manual_id: ID of the manual
            state: New processing state ('queued', 'downloading', 'processing', 'completed', 'failed')
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual:
            raise ValueError(f"Manual with ID {manual_id} not found")
        
        manual.processing_state = state
        
        if state == 'downloading':
            manual.processing_started_at = datetime.utcnow()
        elif state in ('completed', 'failed'):
            manual.processing_completed_at = datetime.utcnow()
        
        self.db.commit()
    
    def _reposition_after(self, position: int) -> None:
        """
        Reposition all items after a given position
        
        Args:
            position: The position after which to reposition
        """
        self.db.query(Manual).filter(
            Manual.queue_position > position
        ).update({
            'queue_position': Manual.queue_position - 1
        })
        self.db.commit()
    
    def get_next_in_queue(self) -> Optional[Manual]:
        """
        Get the next manual to process from the queue
        
        Returns:
            The next manual in queue or None if queue is empty
        """
        return self.db.query(Manual).filter(
            Manual.queue_position == 1,
            Manual.processing_state.in_(['queued', 'failed'])
        ).first()
    
    def mark_processing_complete(self, manual_id: int, success: bool = True, 
                                  resources_zip_path: str = None) -> None:
        """
        Mark a manual as completed processing
        
        Args:
            manual_id: ID of the manual
            success: Whether processing succeeded
            resources_zip_path: Path to generated resources zip file
        """
        manual = self.db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual:
            raise ValueError(f"Manual with ID {manual_id} not found")
        
        manual.processing_state = 'completed' if success else 'failed'
        manual.processing_completed_at = datetime.utcnow()
        manual.resources_zip_path = resources_zip_path
        
        if success:
            manual.status = 'processed'
        else:
            manual.status = 'error'
        
        self.db.commit()
        
        # Remove from queue and reposition
        self.remove_from_queue(manual_id)
